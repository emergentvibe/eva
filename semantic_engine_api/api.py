"""
Eva API Service
------------
REST API for summarization and extraction services.
"""
from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv

from .services.summarization import get_summarization_service
from .services.extraction import ExtractionService
from .services.atomic_ideas import extract_atomic_ideas, get_atomic_idea_extractor
from .agent import ChatAgent

# Load environment variables
load_dotenv()

# Initialize the app
app = Flask(__name__)

# Initialize services
summarization_service = get_summarization_service()
atomic_idea_extractor = get_atomic_idea_extractor()
chat_agent = None

# Base prompt for the agent
AGENT_PROMPT = """You are an AI assistant specialized in explaining messages and providing helpful information. 
Be clear, concise, and helpful in your responses. Avoid judgment and maintain a neutral tone."""

@app.route('/api/summarize', methods=['POST'])
def summarize():
    """API endpoint for summarizing text
    
    Expects a JSON payload with a 'text' field
    Returns a JSON response with 'title' and 'summary' fields
    """
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({"error": "Missing 'text' field in request"}), 400
            
        text = data['text']
        result = summarization_service.generate_summary(text)
        
        return jsonify({
            "title": result['title'],
            "summary": result['summary']
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/agent', methods=['POST'])
def invoke_agent():
    """API endpoint for invoking the agent with an inquiry
    
    Expects a JSON payload with:
    - 'inquiry': The inquiry to process with the agent
    
    Returns a JSON response with the agent's reply
    """
    try:
        global chat_agent
        
        data = request.get_json()
        
        if not data or 'inquiry' not in data:
            return jsonify({"error": "Missing 'inquiry' field in request"}), 400
            
        inquiry = data['inquiry']
        
        # Initialize the agent if not already done
        if not chat_agent or not chat_agent.graph:
            anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
            tavily_api_key = os.getenv("TAVILY_API_KEY")
            
            if not anthropic_api_key:
                return jsonify({"error": "ANTHROPIC_API_KEY not set in environment"}), 500
                
            chat_agent = ChatAgent(
                anthropic_api_key=anthropic_api_key,
                tavily_api_key=tavily_api_key,
                base_prompt=AGENT_PROMPT
            )
            chat_agent.initialize_graph(
                model_name="claude-3-sonnet-20240229",
                temperature=0.7,
                summarization_threshold=10
            )
        
        # Get the response from the agent
        response = chat_agent.run_with_message(inquiry)
        
        return jsonify({
            "response": response
        })
    except Exception as e:
        import traceback
        print(f"Error in invoke_agent: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/api/extract_ideas', methods=['POST'])
def extract_ideas():
    """API endpoint for extracting atomic ideas from text
    
    Expects a JSON payload with a 'text' field
    Returns a JSON response with extracted ideas and scores
    """
    try:
        data = request.get_json()
        
        if not data or 'text' not in data:
            return jsonify({"error": "Missing 'text' field in request"}), 400
            
        text = data['text']
        result = extract_atomic_ideas(text)
        
        # Parse the results into a more structured format
        ideas = []
        if isinstance(result, str):
            for item in result.split(':::'):
                if '|' in item:
                    text_part, score_part = item.rsplit('|', 2)
                    score = int(score_part.strip('|'))
                    ideas.append({"text": text_part.strip(), "score": score})
                else:
                    ideas.append({"text": item.strip(), "score": 0})
        else:
            # If already structured
            ideas = result
            
        return jsonify({
            "ideas": ideas
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/custom_extraction', methods=['POST'])
def custom_extraction():
    """API endpoint for custom extraction with user-defined prompt
    
    Expects a JSON payload with 'text' and 'prompt' fields,
    and optional 'separator', 'parse_score', and 'temperature' fields
    """
    try:
        data = request.get_json()
        
        if not data or 'text' not in data or 'prompt' not in data:
            return jsonify({"error": "Missing required fields. 'text' and 'prompt' are required."}), 400
            
        text = data['text']
        prompt = data['prompt']
        separator = data.get('separator', ':::')
        parse_score = data.get('parse_score', False)
        temperature = data.get('temperature', 0.7)
        
        # Create a one-time extraction service
        extractor = ExtractionService(
            prompt=prompt,
            separator=separator,
            service_name="API Custom Extraction",
            parse_score=parse_score,
            temperature=temperature,
            return_parsed_items=True
        )
        
        result = extractor.extract(text)
        
        return jsonify({
            "result": result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy"})

def create_app(api_key=None):
    """Create the Flask app with configured services
    
    Args:
        api_key (str, optional): API key for Anthropic. Defaults to None.
        
    Returns:
        Flask: Configured Flask app
    """
    global summarization_service, atomic_idea_extractor, chat_agent
    
    # Initialize services with provided API key
    summarization_service = get_summarization_service(api_key=api_key)
    atomic_idea_extractor = get_atomic_idea_extractor(api_key=api_key)
    
    # Initialize chat agent
    anthropic_api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    
    if anthropic_api_key:
        chat_agent = ChatAgent(
            anthropic_api_key=anthropic_api_key,
            tavily_api_key=tavily_api_key,
            base_prompt=AGENT_PROMPT
        )
    
    return app

def run_app(host='0.0.0.0', port=5000, debug=False):
    """Run the Flask app
    
    Args:
        host (str, optional): Host to run on. Defaults to '0.0.0.0'.
        port (int, optional): Port to run on. Defaults to 5000.
        debug (bool, optional): Whether to run in debug mode. Defaults to False.
    """
    port = int(os.environ.get('PORT', port))
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    run_app(debug=False) 