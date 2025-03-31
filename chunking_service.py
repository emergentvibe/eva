from typing import List

# Constants for chunking text
CHUNK_SIZE = 6000  # About 1000 tokens, smaller for idea/tension extraction
CHUNK_OVERLAP = 500  # 125 tokens overlap

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks for processing.
    
    Args:
        text (str): The text to chunk
        chunk_size (int): Size of each chunk (default: 6000)
        overlap (int): Number of characters to overlap between chunks (default: 500)
    
    Returns:
        List[str]: List of text chunks
    """
    print('Starting text chunking...', {'textLength': len(text), 'chunkSize': chunk_size, 'overlap': overlap})
    chunks = []
    start_index = 0
    
    while start_index < len(text):
        end_index = min(start_index + chunk_size, len(text))
        chunk = text[start_index:end_index]
        chunks.append(chunk)
        print(f'Created chunk {len(chunks)}:', {
            'startIndex': start_index,
            'endIndex': end_index,
            'chunkLength': len(chunk)
        })
        
        # If we've reached the end of the text, break
        if end_index == len(text):
            break
        
        # Move start index forward, but ensure we make progress
        start_index = min(end_index - overlap, len(text) - 1)
        # If we're too close to the end to make another meaningful chunk, just break
        if len(text) - start_index < chunk_size / 2:
            break
    
    print('Chunking complete:', {'totalChunks': len(chunks)})
    return chunks 