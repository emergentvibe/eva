"""
Sample Client for Eva API
---------------------
A sample script demonstrating how to use the Eva API endpoints.
"""
import requests
import json
import sys

# Base URL for the API
API_BASE_URL = "http://localhost:5000/api"

def call_summarize_api(text):
    """Call the summarize API endpoint
    
    Args:
        text (str): Text to summarize
        
    Returns:
        dict: Response from API (title and summary)
    """
    url = f"{API_BASE_URL}/summarize"
    payload = {"text": text}
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

def call_extract_ideas_api(text):
    """Call the extract ideas API endpoint
    
    Args:
        text (str): Text to extract ideas from
        
    Returns:
        dict: Response from API (ideas with scores)
    """
    url = f"{API_BASE_URL}/extract_ideas"
    payload = {"text": text}
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

def call_custom_extraction_api(text, prompt, parse_score=True):
    """Call the custom extraction API endpoint
    
    Args:
        text (str): Text to process
        prompt (str): Extraction prompt
        parse_score (bool, optional): Whether to parse scores. Defaults to True.
        
    Returns:
        dict: Response from API (extracted information)
    """
    url = f"{API_BASE_URL}/custom_extraction"
    payload = {
        "text": text,
        "prompt": prompt,
        "parse_score": parse_score,
        "temperature": 0.7
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

def call_health_api():
    """Call the health API endpoint
    
    Returns:
        dict: Response from API (status)
    """
    url = f"{API_BASE_URL}/health"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

def main():
    """Main function to demonstrate API usage"""
    # Check if API is running
    health_result = call_health_api()
    if not health_result:
        print("Error: Could not connect to API. Make sure it's running.")
        sys.exit(1)
    
    print("API is healthy:", health_result)
    print("\n" + "-" * 50 + "\n")
    
    # Sample text for processing
    sample_text = """
    SpaceX successfully launched its Falcon Heavy rocket on Tuesday, marking a significant milestone in private space exploration. 
    The rocket, which is the most powerful operational rocket in the world, carried a Tesla Roadster as its payload. 
    Elon Musk, the CEO of both SpaceX and Tesla, said this was just the beginning of their ambitious plans to make humanity a multi-planetary species. 
    The launch was watched by millions around the world and represents a major step forward in reducing the cost of access to space.
    Despite bad weather conditions earlier in the day, the launch proceeded smoothly with all three boosters performing as expected.
    """
    
    # Example 1: Summarize
    print("EXAMPLE 1: SUMMARIZATION")
    summary_result = call_summarize_api(sample_text)
    if summary_result:
        print(f"Title: {summary_result['title']}")
        print(f"Summary: {summary_result['summary']}")
    
    print("\n" + "-" * 50 + "\n")
    
    # Example 2: Extract Ideas
    print("EXAMPLE 2: ATOMIC IDEA EXTRACTION")
    ideas_result = call_extract_ideas_api(sample_text)
    if ideas_result:
        for i, idea in enumerate(ideas_result['ideas']):
            print(f"{i+1}. {idea['text']} (Score: {idea['score']})")
    
    print("\n" + "-" * 50 + "\n")
    
    # Example 3: Custom Extraction
    print("EXAMPLE 3: CUSTOM EXTRACTION")
    prompt = """
    Extract information about space companies mentioned in the text, along with their achievements.
    Rate each achievement on a scale of 1-5 based on its significance, where 5 is most significant.
    Format as: [Company Name]: [Achievement] |[score]|
    """
    
    custom_result = call_custom_extraction_api(sample_text, prompt)
    if custom_result:
        print("Custom Extraction Result:")
        print(json.dumps(custom_result, indent=2))

if __name__ == "__main__":
    main() 