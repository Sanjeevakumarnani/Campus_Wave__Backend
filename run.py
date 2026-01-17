"""
Development/Local Entry Point
==============================
Usage: python run.py

For production, use wsgi.py with Gunicorn instead.
"""
import os
import sys
from dotenv import load_dotenv
from app import create_app
from app.utils.scheduler import start_background_scheduler

# Load environment variables
load_dotenv()

# Validate required environment variables
REQUIRED_ENV_VARS = ['DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME', 'JWT_SECRET_KEY']
missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if missing:
    print(f"❌ ERROR: Missing required environment variables: {', '.join(missing)}")
    print("Please check your .env file and ensure all required variables are set.")
    sys.exit(1)

# Create Flask application
app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Starting CampusWave Backend Server")
    print("=" * 50)
    
    # Initialize scheduler
    start_background_scheduler(app)
    
    # Bind to 0.0.0.0 to allow connections from Android devices on the network
    # CRITICAL: Debug mode disabled for consistent scheduler execution
    app.run(host='0.0.0.0', port=5000, debug=False)
