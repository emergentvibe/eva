import logging
from typing import Dict, List, Optional, Union
from anthropic import Anthropic
from dotenv import load_dotenv
import os

load_dotenv()

class ExtractionService:
    def __init__(self, 
                 prompt: str,
                 separator: str = ':::',
                 model: str = 'claude-3-sonnet-20240229',
                 temperature: float = 0.7,
                 service_name: str = 'Generic',
                 parse_score: bool = False,
                 return_parsed_items: bool = False,
                 incremental_prompt: Optional[str] = None):
        """Initialize the ExtractionService.

        Args:
            prompt (str): The prompt template for extraction
            separator (str, optional): Separator for items. Defaults to ':::'.
            model (str, optional): Model to use. Defaults to 'claude-3-sonnet-20240229'.
            temperature (float, optional): Temperature for generation. Defaults to 0.7.
            service_name (str, optional): Name of the service. Defaults to 'Generic'.
            parse_score (bool, optional): Whether to parse scores. Defaults to False.
            return_parsed_items (bool, optional): Whether to return parsed items. Defaults to False.
            incremental_prompt (Optional[str], optional): Prompt for incremental updates. Defaults to None.
        """
        self.prompt = prompt
        self.incremental_prompt = incremental_prompt or prompt
        self.separator = separator
        self.model = model
        self.temperature = temperature
        self.service_name = service_name
        self.parse_score = parse_score
        self.return_parsed_items = return_parsed_items
        self.client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        # Set up logging
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        self.logger.info('Service initialized', extra={
            'model': model,
            'temperature': temperature,
            'parse_score': parse_score,
            'return_parsed_items': return_parsed_items,
            'has_incremental_prompt': bool(incremental_prompt)
        })

    def parse_item_with_score(self, item: str) -> Dict[str, Union[str, int]]:
        """Parse an item that may contain a score.

        Args:
            item (str): The item to parse

        Returns:
            Dict[str, Union[str, int]]: Dictionary containing text and score
        """
        self.logger.debug('Parsing item', extra={'item': item})
        
        # Clean up the item - remove extra newlines and whitespace
        clean_item = ' '.join(item.split())
        
        # Remove any trailing punctuation before parsing
        cleaned_for_parsing = clean_item.rstrip('.,!?').strip()
        
        # Check for score at the end using strict regex
        import re
        match = re.match(r'(.*?)\s*\|(\d+)\|\s*$', cleaned_for_parsing)
        
        if match:
            result = {
                'text': match.group(1).strip(),
                'score': int(match.group(2))
            }
            self.logger.debug('Successfully parsed item', extra={
                'original': clean_item,
                'cleaned_for_parsing': cleaned_for_parsing,
                'result': result,
                'match_groups': match.groups()
            })
            return result
        
        self.logger.debug('No score found, using default', extra={
            'original': item,
            'cleaned': clean_item,
            'cleaned_for_parsing': cleaned_for_parsing
        })
        return {'text': clean_item, 'score': 0}

    def extract(self, text: str, options: Dict = None) -> Union[str, List[Dict[str, Union[str, int]]]]:
        """Extract information from text.

        Args:
            text (str): Text to extract from
            options (Dict, optional): Additional options. Defaults to None.

        Returns:
            Union[str, List[Dict[str, Union[str, int]]]]: Extracted information
        """
        options = options or {}
        previous_text = options.get('previous_text', '')
        previous_results = options.get('previous_results', [])
        processed_length = options.get('processed_length', 0)
        
        self.logger.info('Starting extraction', extra={
            'text_length': len(text),
            'previous_text_length': len(previous_text),
            'previous_results_count': len(previous_results),
            'processed_length': processed_length,
            'parse_score': self.parse_score,
            'service_name': self.service_name,
            'is_incremental': bool(previous_text)
        })

        # Determine if this is an incremental update
        is_incremental = bool(previous_text and previous_results)
        
        # Format the prompt based on whether this is incremental or not
        prompt_template = self.incremental_prompt if is_incremental else self.prompt
        formatted_previous_results = ''
        
        if is_incremental:
            formatted_previous_results = self.separator.join(
                f"{item['text']} |{item['score']}|" if self.parse_score else item['text']
                for item in previous_results
            )

        full_prompt = (
            prompt_template
            .replace('{previous_text}', previous_text)
            .replace('{new_text}', text)
            .replace('{previous_results}', formatted_previous_results)
            if is_incremental
            else f"{prompt_template}\n\nContent:\n{text}"
        )

        try:
            self.logger.debug('Sending request to Anthropic', extra={
                'model': self.model,
                'temperature': self.temperature,
                'prompt_length': len(full_prompt),
                'is_incremental': is_incremental
            })

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                temperature=self.temperature,
                messages=[{
                    "role": "user",
                    "content": full_prompt
                }]
            )

            result = response.content[0].text
            self.logger.debug('Received raw result', extra={
                'result_length': len(result),
                'preview': result[:100] + '...',
                'full_result': result
            })
            
            if self.parse_score:
                # Clean up the entire result string first
                clean_result = result.strip().rstrip('.,!?')
                
                # Split by either ::: or newlines, then clean up each item
                items = [
                    item.strip() for item in clean_result.split(self.separator)
                    if item.strip()
                ]

                self.logger.debug('Split result into items', extra={
                    'original_result': result,
                    'clean_result': clean_result,
                    'count': len(items),
                    'items': items
                })
                
                parsed_items = []
                for item in items:
                    parsed = self.parse_item_with_score(item)
                    self.logger.debug('Parsed item result', extra={
                        'original': item,
                        'parsed': parsed,
                        'has_valid_score': parsed['score'] > 0
                    })
                    if parsed['text'] and parsed['score'] >= 0:
                        parsed_items.append(parsed)
                    else:
                        self.logger.warning('Filtered out invalid item', extra={'item': parsed})
                
                if not parsed_items:
                    self.logger.warning('No valid items were parsed from the result', extra={
                        'raw_result': result
                    })
                
                self.logger.info('Extraction complete', extra={
                    'item_count': len(parsed_items),
                    'average_score': sum(item['score'] for item in parsed_items) / len(parsed_items) if parsed_items else 0,
                    'items': [{
                        'text': item['text'][:50] + '...',
                        'score': item['score']
                    } for item in parsed_items]
                })

                # Return either parsed items or formatted string based on flag
                if self.return_parsed_items:
                    return parsed_items
                return self.separator.join(f"{item['text']} |{item['score']}|" for item in parsed_items)
            
            self.logger.info('Extraction complete', extra={
                'result_length': len(result),
                'is_incremental': is_incremental
            })
            return result
        except Exception as error:
            self.logger.error('Extraction failed', extra={
                'error': str(error),
                'service_name': self.service_name,
                'is_incremental': is_incremental
            })
            raise 