import openai from './openaiService.js';
import { chunkText } from './chunkingService.js';
import { createServiceLogger } from './loggingService.js';

export class ExtractionService {
    constructor({ 
        prompt, 
        separator = ':::', 
        model = 'gpt-4',
        temperature = 0.7,
        serviceName = 'Generic',
        parseScore = false,
        returnParsedItems = false,
        incrementalPrompt = null
    }) {
        this.prompt = prompt;
        this.incrementalPrompt = incrementalPrompt || prompt;
        this.separator = separator;
        this.model = model;
        this.temperature = temperature;
        this.serviceName = serviceName;
        this.parseScore = parseScore;
        this.returnParsedItems = returnParsedItems;
        this.openai = openai;
        this.logger = createServiceLogger(serviceName);
        
        this.logger.info('Service initialized', {
            model,
            temperature,
            parseScore,
            returnParsedItems,
            hasIncrementalPrompt: !!incrementalPrompt
        });
    }

    parseItemWithScore(item) {
        this.logger.debug('Parsing item', { item });
        
        // Clean up the item - remove extra newlines and whitespace
        const cleanItem = item.replace(/\n+/g, ' ').trim();
        
        // Remove any trailing punctuation before parsing
        const cleanedForParsing = cleanItem.replace(/[.,!?]+$/, '').trim();
        
        // Check for score at the end using strict regex
        const match = cleanedForParsing.match(/(.*?)\s*\|(\d+)\|\s*$/);
        
        if (match) {
            const result = {
                text: match[1].trim(),
                score: parseInt(match[2], 10)
            };
            this.logger.debug('Successfully parsed item', { 
                original: cleanItem,
                cleanedForParsing,
                result,
                matchGroups: match
            });
            return result;
        }
        
        this.logger.debug('No score found, using default', { 
            original: item,
            cleaned: cleanItem,
            cleanedForParsing
        });
        return { text: cleanItem, score: 0 };
    }

    async extract(text, options = {}) {
        const { previousText = '', previousResults = [], processedLength = 0 } = options;
        
        this.logger.info('Starting extraction', {
            textLength: text.length,
            previousTextLength: previousText.length,
            previousResultsCount: previousResults.length,
            processedLength,
            parseScore: this.parseScore,
            serviceName: this.serviceName,
            isIncremental: !!previousText
        });

        // Determine if this is an incremental update
        const isIncremental = previousText.length > 0 && previousResults.length > 0;
        
        // Format the prompt based on whether this is incremental or not
        const promptTemplate = isIncremental ? this.incrementalPrompt : this.prompt;
        const formattedPreviousResults = isIncremental ? 
            previousResults.map(item => this.parseScore ? 
                `${item.text} |${item.score}|` : 
                item.text
            ).join(this.separator) :
            '';

        const fullPrompt = isIncremental ?
            promptTemplate
                .replace('{previous_text}', previousText)
                .replace('{new_text}', text)
                .replace('{previous_results}', formattedPreviousResults) :
            `${promptTemplate}\n\nContent:\n${text}`;

        try {
            this.logger.debug('Sending request to OpenAI', {
                model: this.model,
                temperature: this.temperature,
                promptLength: fullPrompt.length,
                isIncremental
            });

            const completion = await this.openai.chat.completions.create({
                model: this.model,
                messages: [{
                    role: "user",
                    content: fullPrompt
                }],
                temperature: this.temperature
            });

            const result = completion.choices[0].message.content;
            this.logger.debug('Received raw result', {
                resultLength: result.length,
                preview: result.substring(0, 100) + '...',
                fullResult: result
            });
            
            if (this.parseScore) {
                // Clean up the entire result string first
                const cleanResult = result.trim().replace(/[.,!?]+$/, '');
                
                // Split by either ::: or newlines, then clean up each item
                const items = cleanResult
                    .split(/:::|\n/)
                    .map(item => item.trim())
                    .filter(item => item && item.length > 0);

                this.logger.debug('Split result into items', { 
                    originalResult: result,
                    cleanResult,
                    count: items.length,
                    items: items
                });
                
                const parsedItems = items.map(item => {
                    const parsed = this.parseItemWithScore(item);
                    this.logger.debug('Parsed item result', {
                        original: item,
                        parsed: parsed,
                        hasValidScore: parsed.score > 0
                    });
                    return parsed;
                }).filter(item => {
                    const isValid = item.text && item.score >= 0;
                    if (!isValid) {
                        this.logger.warn('Filtered out invalid item', { item });
                    }
                    return isValid;
                });
                
                if (parsedItems.length === 0) {
                    this.logger.warn('No valid items were parsed from the result', {
                        rawResult: result
                    });
                }
                
                this.logger.info('Extraction complete', {
                    itemCount: parsedItems.length,
                    averageScore: parsedItems.length > 0 
                        ? parsedItems.reduce((sum, item) => sum + item.score, 0) / parsedItems.length 
                        : 0,
                    items: parsedItems.map(item => ({
                        text: item.text.substring(0, 50) + '...',
                        score: item.score
                    }))
                });

                // Return either parsed items or formatted string based on flag
                if (this.returnParsedItems) {
                    return parsedItems;
                }
                return parsedItems.map(item => `${item.text} |${item.score}|`).join(':::');
            }
            
            this.logger.info('Extraction complete', {
                resultLength: result.length,
                isIncremental
            });
            return result;
        } catch (error) {
            this.logger.error('Extraction failed', {
                error: error.message,
                stack: error.stack,
                serviceName: this.serviceName,
                isIncremental
            });
            throw error;
        }
    }
} 