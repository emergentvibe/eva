"""
Eva Bot Starter
-------------
Script to start both the API service and the Eva bot.
"""
import os
import sys
import subprocess
import time
import signal
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("eva.log")
    ]
)
logger = logging.getLogger("eva-starter")

# Global variables for process management
api_process = None
bot_process = None

def start_api():
    """Start the API service"""
    logger.info("Starting Eva API service...")
    try:
        api_cmd = [sys.executable, "-m", "semantic_engine_api.run"]
        api_process = subprocess.Popen(
            api_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        logger.info(f"API service started with PID: {api_process.pid}")
        return api_process
    except Exception as e:
        logger.error(f"Failed to start API service: {str(e)}")
        return None

def start_bot():
    """Start the Eva Discord bot"""
    logger.info("Starting Eva Discord bot...")
    try:
        bot_cmd = [sys.executable, "run_bot.py"]
        bot_process = subprocess.Popen(
            bot_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        logger.info(f"Bot started with PID: {bot_process.pid}")
        return bot_process
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}")
        return None

def log_output(process, process_name):
    """Log process output in a non-blocking way"""
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            logger.info(f"{process_name} | {output.strip()}")
    
    # Check for errors on process exit
    return_code = process.poll()
    if return_code is not None and return_code != 0:
        stderr = process.stderr.read()
        logger.error(f"{process_name} exited with code {return_code}: {stderr}")

def cleanup(signum=None, frame=None):
    """Clean up processes on exit"""
    logger.info("Shutting down Eva services...")
    
    # Terminate API process
    if api_process and api_process.poll() is None:
        logger.info(f"Terminating API process (PID: {api_process.pid})")
        api_process.terminate()
        api_process.wait(timeout=5)
    
    # Terminate bot process
    if bot_process and bot_process.poll() is None:
        logger.info(f"Terminating bot process (PID: {bot_process.pid})")
        bot_process.terminate()
        bot_process.wait(timeout=5)
    
    logger.info("Eva services shut down successfully")
    
    # Exit if this was called as a signal handler
    if signum is not None:
        sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    try:
        # Start API service
        api_process = start_api()
        if not api_process:
            logger.error("Failed to start API service. Exiting.")
            sys.exit(1)
        
        # Allow API time to initialize
        logger.info("Waiting for API to initialize...")
        time.sleep(5)
        
        # Start bot
        bot_process = start_bot()
        if not bot_process:
            logger.error("Failed to start bot. Shutting down.")
            cleanup()
            sys.exit(1)
        
        # Start output logging threads
        import threading
        api_log_thread = threading.Thread(target=log_output, args=(api_process, "API"))
        bot_log_thread = threading.Thread(target=log_output, args=(bot_process, "BOT"))
        
        api_log_thread.daemon = True
        bot_log_thread.daemon = True
        
        api_log_thread.start()
        bot_log_thread.start()
        
        # Main monitoring loop
        while True:
            # Check if processes are still running
            api_status = api_process.poll()
            bot_status = bot_process.poll()
            
            if api_status is not None:
                logger.error(f"API process exited unexpectedly with code {api_status}")
                cleanup()
                sys.exit(1)
            
            if bot_status is not None:
                logger.error(f"Bot process exited unexpectedly with code {bot_status}")
                cleanup()
                sys.exit(1)
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        cleanup()
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        cleanup()
        sys.exit(1) 