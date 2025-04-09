import os
import whisper
import requests
import json

# Initialize whisper model for audio transcription
model = whisper.load_model("small")

# Base URL for the API
API_BASE_URL = "http://localhost:5000/api"

def summarize_message(content: str) -> dict:
    """Summarize a message using the API service
    
    Args:
        content (str): Message content to summarize
        
    Returns:
        dict: Dictionary containing 'title' and 'summary' keys
    """
    print(f"[DEBUG] Summarizing message via API: {content[:100]}...")
    
    try:
        url = f"{API_BASE_URL}/summarize"
        payload = {"text": content}
        
        response = requests.post(url, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            print(f"[DEBUG] Summary received from API")
            return result
        else:
            print(f"[ERROR] API returned status code {response.status_code}: {response.text}")
            return {"title": "Error generating summary", "summary": "An error occurred while generating the summary."}
    except Exception as e:
        print(f"[ERROR] Exception in summarize_message: {str(e)}")
        return {"title": "Error generating summary", "summary": f"An error occurred: {str(e)}"}

async def get_transcripts_from_audio_data(audio_data):
    """Process audio data and return transcripts
    
    Args:
        audio_data (dict): Dictionary of user IDs to audio data
        
    Returns:
        dict: Dictionary of user IDs to transcripts
    """
    print("[DEBUG] Starting transcript processing")
    print(f"[DEBUG] Audio data received: {list(audio_data.keys())}")
    
    transcripts = {}
    for user_id, audio in audio_data.items():
        print(f"[DEBUG] Processing audio for user: {user_id}")
        filename = f"audio_{user_id}.wav"
        with open(filename, "wb") as f:
            f.write(audio.getvalue())
        
        print(f"[DEBUG] Saved audio file: {filename}")
        # Transcribe with whisper
        text = model.transcribe(filename)["text"]
        print(f"[DEBUG] Transcribed text: {text}")
        os.remove(filename)
        transcripts[user_id] = text
    
    print(f"[DEBUG] Final transcripts: {transcripts}")
    return transcripts

async def answer_prompts(transcripts, channel):
    """Process transcripts and send responses
    
    Args:
        transcripts (dict): Dictionary of user IDs to transcripts
        channel (discord.TextChannel): Channel to send responses in
    """
    print("[DEBUG] Starting answer_prompts")
    print(f"[DEBUG] Received transcripts type: {type(transcripts)}")
    print(f"[DEBUG] Received transcripts: {transcripts}")

    for user_id, text in transcripts.items():
        print(f"[DEBUG] Processing response for user: {user_id}")
        await channel.send(f"{user_id} said: {text}")
        print(f"[DEBUG] Sent response for user: {user_id}")

async def get_related_topics(message: str) -> str:
    """Get related topics for a message
    
    Args:
        message (str): Message to get related topics for
        
    Returns:
        str: Related topics
    """
    # Call custom extraction API with a related topics prompt
    try:
        url = f"{API_BASE_URL}/custom_extraction"
        prompt = """Generate a list of 5-10 related topics that the user might be interested in exploring based on their message. 
        Format each topic as a simple phrase without numbering or bullets."""
        
        payload = {
            "text": message,
            "prompt": prompt,
            "parse_score": False,
            "temperature": 0.7
        }
        
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            topics = result['result']
            return topics
        else:
            print(f"[ERROR] API returned status code {response.status_code}: {response.text}")
            return "Related topics service not available at the moment."
    except Exception as e:
        print(f"[ERROR] Exception in get_related_topics: {str(e)}")
        return "Related topics service not available at the moment."

async def fact_check_claim(claim: str) -> str:
    """Fact check a claim
    
    Args:
        claim (str): Claim to fact check
        
    Returns:
        str: Fact check result
    """
    # Call custom extraction API with a fact-checking prompt
    try:
        url = f"{API_BASE_URL}/custom_extraction"
        prompt = """Analyze the following claim for accuracy. Provide a breakdown of what parts are factual and 
        what parts may need verification. Rate the overall claim on a scale of 1-5 where 1 is 'likely false' and 5 is 'likely true'."""
        
        payload = {
            "text": claim,
            "prompt": prompt,
            "parse_score": False,
            "temperature": 0.3
        }
        
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return result['result']
        else:
            print(f"[ERROR] API returned status code {response.status_code}: {response.text}")
            return "Fact checking service not available at the moment."
    except Exception as e:
        print(f"[ERROR] Exception in fact_check_claim: {str(e)}")
        return "Fact checking service not available at the moment."

async def get_definition(term: str, context: str = None) -> str:
    """Get definition for a term
    
    Args:
        term (str): Term to define
        context (str, optional): Context for the term. Defaults to None.
        
    Returns:
        str: Definition
    """
    # Call custom extraction API with a definition prompt
    try:
        url = f"{API_BASE_URL}/custom_extraction"
        
        if context:
            prompt = f"""Define the term '{term}' in the following context: '{context}'. 
            Provide a clear, concise definition along with any relevant information that helps understand the term in this specific context."""
        else:
            prompt = f"""Define the term '{term}'. Provide a clear, concise definition that would be helpful to someone unfamiliar with this term.
            Include any important related concepts or applications of this term."""
            
        payload = {
            "text": context or term,
            "prompt": prompt,
            "parse_score": False,
            "temperature": 0.3
        }
        
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return result['result']
        else:
            print(f"[ERROR] API returned status code {response.status_code}: {response.text}")
            return "Definition service not available at the moment."
    except Exception as e:
        print(f"[ERROR] Exception in get_definition: {str(e)}")
        return "Definition service not available at the moment."

async def extract_atomic_ideas(text: str) -> list:
    """Extract atomic ideas from text
    
    Args:
        text (str): Text to extract ideas from
        
    Returns:
        list: List of ideas with scores
    """
    try:
        url = f"{API_BASE_URL}/extract_ideas"
        payload = {"text": text}
        
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            return result['ideas']
        else:
            print(f"[ERROR] API returned status code {response.status_code}: {response.text}")
            return []
    except Exception as e:
        print(f"[ERROR] Exception in extract_atomic_ideas: {str(e)}")
        return []

def check_api_health() -> bool:
    """Check if the API is healthy
    
    Returns:
        bool: True if healthy, False if not
    """
    try:
        url = f"{API_BASE_URL}/health"
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except:
        return False 