"""
Run the Eva API
-------------
Script to run the Eva API service.
"""
import os
from dotenv import load_dotenv
from api_module.api import create_app, run_app

if __name__ == '__main__':
    # Load environment variables
    load_dotenv()
    
    # Get API key from environment
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    # Create app with API key
    app = create_app(api_key=api_key)
    
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    run_app(host='0.0.0.0', port=port, debug=False) 