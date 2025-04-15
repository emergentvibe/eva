import os
import whisper
import requests
import json
import datetime
import logging
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("eva-utils")

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
    logger.info(f"Summarizing message via API: {content[:100]}...")
    
    try:
        url = f"{API_BASE_URL}/summarize"
        payload = {"text": content}
        
        response = requests.post(url, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Summary received from API")
            return result
        else:
            logger.error(f"API returned status code {response.status_code}: {response.text}")
            return {"title": "Error generating summary", "summary": "An error occurred while generating the summary."}
    except Exception as e:
        logger.error(f"Exception in summarize_message: {str(e)}")
        logger.error(traceback.format_exc())
        return {"title": "Error generating summary", "summary": f"An error occurred: {str(e)}"}

async def invoke_agent(message_content: str, author_username: str, requester_username: str, explanation_request: str = "") -> str:
    """Invoke the agent with a constructed inquiry
    
    Args:
        message_content (str): Content of the message to explain
        author_username (str): Username of the message author
        requester_username (str): Username of the person making the request
        explanation_request (str, optional): What aspect to explain. Defaults to "".
        
    Returns:
        str: Agent's response
    """
    logger.info(f"Invoking agent via API for message from {author_username}, requested by {requester_username}")
    logger.info(f"Message content snippet: {message_content[:100]}...")
    
    if explanation_request:
        logger.info(f"Explanation request: {explanation_request}")
    
    try:
        # Construct the inquiry here rather than in the API
        if explanation_request:
            inquiry = f"{requester_username} is asking: Can you explain what {author_username} meant in this message, specifically about {explanation_request}? Message: {message_content}"
        else:
            inquiry = f"{requester_username} is asking: Can you explain what {author_username} meant in this message? Message: {message_content}"
        
        logger.debug(f"Full inquiry: {inquiry}")
        url = f"{API_BASE_URL}/agent"
        payload = {"inquiry": inquiry}
        
        logger.info(f"Sending request to {url}")
        response = requests.post(url, json=payload, timeout=120)
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Response received from agent API with status code 200")
            
            if not result or "response" not in result:
                logger.error(f"API returned unexpected response format: {result}")
                return "Error: API returned unexpected response format"
                
            agent_response = result.get("response", "No response was generated.")
            logger.info(f"Agent response snippet: {agent_response[:100]}...")
            return agent_response
        else:
            logger.error(f"API returned status code {response.status_code}")
            logger.error(f"Response text: {response.text}")
            
            # Try to parse error message from JSON if available
            try:
                error_data = response.json()
                error_message = error_data.get("error", str(response.text))
                logger.error(f"Error from API: {error_message}")
                return f"Error from agent API: {error_message}"
            except:
                return f"Error from agent API: Status code {response.status_code}"
    except requests.exceptions.Timeout:
        error_msg = f"Request to agent API timed out after 120 seconds"
        logger.error(error_msg)
        return f"Error invoking agent: {error_msg}"
    except requests.exceptions.ConnectionError:
        error_msg = f"Connection error when connecting to agent API. Make sure the API server is running."
        logger.error(error_msg)
        return f"Error invoking agent: {error_msg}"
    except Exception as e:
        logger.error(f"Exception in invoke_agent: {str(e)}")
        logger.error(traceback.format_exc())
        return f"Error invoking agent: {str(e)}"

async def get_transcripts_from_audio_data(audio_data):
    """Process audio data and return transcripts with timestamps
    
    Args:
        audio_data (dict): Dictionary of user IDs to audio data
        
    Returns:
        dict: Dictionary of user IDs to transcripts with timestamps
    """
    logger.info("Starting transcript processing")
    logger.info(f"Audio data received: {list(audio_data.keys())}")
    
    transcripts = {}
    for user_id, audio in audio_data.items():
        logger.info(f"Processing audio for user: {user_id}")
        filename = f"audio_{user_id}.wav"
        with open(filename, "wb") as f:
            f.write(audio.getvalue())
        
        logger.info(f"Saved audio file: {filename}")
        # Transcribe with whisper and request word timestamps
        result = model.transcribe(filename, word_timestamps=True)
        
        # Extract text and timestamps for each segment
        segments = []
        for segment in result["segments"]:
            segments.append({
                "text": segment["text"],
                "start": segment["start"],
                "end": segment["end"]
            })
        
        logger.info(f"Transcribed {len(segments)} segments with timestamps")
        os.remove(filename)
        transcripts[user_id] = segments
    
    logger.debug(f"Final transcripts with timestamps: {transcripts}")
    return transcripts

async def answer_prompts(transcripts, channel):
    """Process transcripts and send responses in a chronological timeline
    
    Args:
        transcripts (dict): Dictionary of user IDs to transcripts with timestamps
        channel (discord.TextChannel): Channel to send responses in
    """
    print("[DEBUG] Starting answer_prompts")
    print(f"[DEBUG] Received transcripts type: {type(transcripts)}")
    
    # Create timestamp for thread name
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    thread_name = f"Transcript {timestamp}"
    
    # Create a message to start the thread from
    initial_message = await channel.send(f"New voice transcription completed at {timestamp}")
    
    # Create the thread
    thread = await initial_message.create_thread(name=thread_name)
    print(f"[DEBUG] Created thread: {thread_name}")
    
    # First message in thread summarizing participants
    participants = ", ".join(transcripts.keys())
    await thread.send(f"Participants: {participants}")
    
    # Prepare an interlaced timeline
    timeline = []
    
    # Collect all segments from all speakers
    for user_id, segments in transcripts.items():
        for segment in segments:
            timeline.append({
                "user_id": user_id,
                "text": segment["text"],
                "start": segment["start"],
                "end": segment["end"]
            })
    
    # Sort the combined timeline by start time
    timeline.sort(key=lambda x: x["start"])
    
    # Format and send the timeline
    await thread.send("## Conversation Timeline")
    
    current_message = ""
    for item in timeline:
        # Format: [00:15] @User: This is what they said
        time_str = f"[{int(item['start']//60):02d}:{int(item['start']%60):02d}]"
        line = f"{time_str} {item['user_id']}: {item['text']}\n"
        
        # Check if adding this line would exceed Discord's message limit
        if len(current_message + line) > 1900:
            # Send current message and start a new one
            await thread.send(current_message)
            current_message = line
        else:
            current_message += line
    
    # Send any remaining content
    if current_message:
        await thread.send(current_message)
    
    print(f"[DEBUG] Sent interlaced timeline in thread")

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
        logger.info(f"Checking API health at {url}")
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            logger.info("API health check successful")
            return True
        else:
            logger.error(f"API health check failed with status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error during API health check: {str(e)}")
        return False
    except requests.exceptions.Timeout as e:
        logger.error(f"Timeout during API health check: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error during API health check: {str(e)}")
        logger.error(traceback.format_exc())
        return False 