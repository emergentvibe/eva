import os
import whisper
from summarisation_service import get_summarization_service

# Initialize services
model = whisper.load_model("small")
summarization_service = get_summarization_service()

def summarize_message(content: str) -> dict:
    """Summarize a message using the summarization service

    Args:
        content (str): Message content to summarize

    Returns:
        dict: Dictionary containing 'title' and 'summary' keys
    """
    print(f"[DEBUG] Summarizing message: {content}")
    result = summarization_service.generate_summary(content)
    print(f"[DEBUG] Summary result: {result}")
    return result

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
    # TODO: Implement related topics service
    return "Related topics service not yet implemented"

async def fact_check_claim(claim: str) -> str:
    """Fact check a claim

    Args:
        claim (str): Claim to fact check

    Returns:
        str: Fact check result
    """
    # TODO: Implement fact checking service
    return "Fact checking service not yet implemented"

async def get_definition(term: str, context: str = None) -> str:
    """Get definition for a term

    Args:
        term (str): Term to define
        context (str, optional): Context for the term. Defaults to None.

    Returns:
        str: Definition
    """
    # TODO: Implement definition service
    return "Definition service not yet implemented"

async def get_chat_response(message: str) -> str:
    """Get chat response for a message

    Args:
        message (str): Message to respond to

    Returns:
        str: Chat response
    """
    # TODO: Implement chat service
    return "Chat service not yet implemented" 