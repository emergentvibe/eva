from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from summarisation_service import get_summarization_service
from extraction_service import ExtractionService
from atomic_idea_extractor import atomic_idea_extractor

# Load environment variables
load_dotenv()

# Initialize the app
app = Flask(__name__)

# Initialize services
summarization_service = get_summarization_service()

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
        result = atomic_idea_extractor.extract(text)
        
        # Parse the results into a more structured format
        ideas = []
        if isinstance(result, str):
            for item in result.split(':::'):
                if '|' in item:
                    text, score_part = item.rsplit('|', 2)
                    score = int(score_part.strip('|'))
                    ideas.append({"text": text.strip(), "score": score})
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 