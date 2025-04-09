"""
Summarization Service
-------------------
Service for generating summaries and titles from text.
"""
import os
from typing import Optional, Dict, List
from anthropic import Anthropic
from dotenv import load_dotenv
from .chunking import chunk_text

load_dotenv()

class SummarizationService:
    # Constants for title generation
    TITLE_MAX_TOKENS = 80
    TITLE_TEMPERATURE = 0.3
    SUMMARY_TEMPERATURE = 0.4
    SUMMARY_MAX_TOKENS = 1000
    MERGE_MAX_TOKENS = 2000

    def __init__(self, api_key=None):
        self.client = Anthropic(api_key=api_key or os.getenv('ANTHROPIC_API_KEY'))

    def generate_title(self, text: str) -> str:
        try:
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=self.TITLE_MAX_TOKENS,
                temperature=self.TITLE_TEMPERATURE,
                messages=[{
                    "role": "user",
                    "content": "Generate a short, descriptive title (max 50 characters) that captures the main topic or theme of the text. The title should be concise but informative. Text:" + text
                }]
            )

            title = response.content[0].text.strip()
            return title
        except Exception as error:
            print('Error generating title:', error)
            raise

    def generate_summary(self, text: str) -> Dict[str, str]:
        print('\n=== Starting Summary Generation ===')
        print('Input text length:', len(text))
        
        try:
            # Get chunks using the shared chunking service
            chunks = chunk_text(text)
            print(f"Processing {len(chunks)} chunks for summary")

            # Process chunks sequentially to manage memory
            chunk_summaries = []
            for i, chunk in enumerate(chunks):
                print(f"\n--- Processing Chunk {i + 1}/{len(chunks)} for Summary ---")
                summary = self._generate_summary_for_chunk(chunk, i)
                chunk_summaries.append(summary)
                chunks[i] = None  # Clear processed chunk from memory
                
            # If we only have one chunk, use its summary directly
            if len(chunk_summaries) == 1:
                final_summary = chunk_summaries[0]
            else:
                # Merge the summaries if we have multiple chunks
                print('\nMerging summaries...')
                final_summary = self._merge_summaries(chunk_summaries)

            # Generate title from the final summary
            print('\nGenerating title...')
            title = self.generate_title(final_summary)
            print('Title generated:', title)

            return {'title': title, 'summary': final_summary}
        except Exception as error:
            print('\nError in generate_summary:', error)
            raise

    def _generate_summary_for_chunk(self, chunk: str, index: int) -> str:
        try:
            print(f"Processing chunk {index + 1}:", {'chunkLength': len(chunk)})
            
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=self.SUMMARY_MAX_TOKENS,
                temperature=self.SUMMARY_TEMPERATURE,
                messages=[{
                    "role": "user",
                    "content": "You are a highly skilled editor. Create a detailed analysis that captures the key points and main ideas of the following journal entry text while improving flow and clarity. The user is journaling in a stream of consciousness style. journal entry: " + chunk
                }]
            )

            summary = response.content[0].text
            print(f"Completed chunk {index + 1} summary:", {'summaryLength': len(summary)})
            
            return summary
        except Exception as error:
            print(f"Error generating summary for chunk {index + 1}:", error)
            raise

    def _merge_summaries(self, summaries: List[str]) -> str:
        try:
            print('Starting summary merge...', {'numberOfSummaries': len(summaries)})
            
            summaries_text = '\n\n'.join(
                f"Part {i + 1}:\n{s}" for i, s in enumerate(summaries)
            )

            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=self.MERGE_MAX_TOKENS,
                temperature=self.SUMMARY_TEMPERATURE,
                messages=[{
                    "role": "user",
                    "content": f"You are a skilled editor merging multiple summaries into a single coherent document. Maintain the key points while ensuring smooth transitions and avoiding redundancy. Below are summaries of different parts of a longer document. Please merge them into a single coherent summary:\n\n{summaries_text}"
                }]
            )

            merged_summary = response.content[0].text
            print('Merge complete:', {'mergedSummaryLength': len(merged_summary)})
            return merged_summary
        except Exception as error:
            print('Error merging summaries:', error)
            raise

# Create a singleton instance
_instance = None

def get_summarization_service(api_key=None) -> SummarizationService:
    global _instance
    if _instance is None:
        _instance = SummarizationService(api_key=api_key)
    return _instance 