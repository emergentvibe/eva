import { ExtractionService } from './ExtractionService.js';

const atomicIdeaExtractor = new ExtractionService({
    prompt: `Extract the key atomic ideas from this text. Each idea should be self-contained complete and concise. After each idea, rate its importance from 1-5 where 5 is most critical to the text's meaning. Separate ideas with three colons (:::). Focus on unique, non-redundant ideas. Format as: [idea] |[score]]

    Example usage on a text:
SpaceX launched their new rocket yesterday, marking their 100th successful mission. The launch was delayed three times due to weather.

Would output:
SpaceX completed their 100th successful mission|5|:::The latest launch happened yesterday|2|:::Weather caused three launch delays|1|`,
    serviceName: "Atomic Ideas",
    parseScore: true,
    temperature: 0.7
});

export const extractAtomicIdeas = (text) => atomicIdeaExtractor.extract(text); 