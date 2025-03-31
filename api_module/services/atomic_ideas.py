"""
Atomic Idea Extractor
-------------------
Service for extracting key atomic ideas from text.
"""
from .extraction import ExtractionService

# Create the atomic idea extractor instance
def create_atomic_idea_extractor(api_key=None):
    """Create an extraction service for atomic ideas
    
    Args:
        api_key (str, optional): API key for Anthropic. Defaults to None.
        
    Returns:
        ExtractionService: Extraction service for atomic ideas
    """
    return ExtractionService(
        prompt="""Extract the key atomic ideas from this text. Each idea should be self-contained complete and concise. After each idea, rate its importance from 1-5 where 5 is most critical to the text's meaning. Separate ideas with three colons (:::). Focus on unique, non-redundant ideas. Format as: [idea] |[score]|

Example usage on a text:
SpaceX launched their new rocket yesterday, marking their 100th successful mission. The launch was delayed three times due to weather.

Would output:
SpaceX completed their 100th successful mission|5|:::The latest launch happened yesterday|2|:::Weather caused three launch delays|1|""",
        service_name="Atomic Ideas",
        parse_score=True,
        temperature=0.7,
        api_key=api_key
    )

# Singleton instance
_instance = None

def get_atomic_idea_extractor(api_key=None):
    """Get (or create) the atomic idea extractor instance
    
    Args:
        api_key (str, optional): API key for Anthropic. Defaults to None.
        
    Returns:
        ExtractionService: Extraction service for atomic ideas
    """
    global _instance
    if _instance is None:
        _instance = create_atomic_idea_extractor(api_key=api_key)
    return _instance

def extract_atomic_ideas(text: str) -> str:
    """Extract atomic ideas from text.

    Args:
        text (str): Text to extract atomic ideas from

    Returns:
        str: Extracted atomic ideas with scores
    """
    return get_atomic_idea_extractor().extract(text) 