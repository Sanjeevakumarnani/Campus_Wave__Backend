"""
Production WSGI Entry Point
============================
Usage: gunicorn -w 4 -b 0.0.0.0:5000 wsgi:application

For AWS EC2 with Nginx:
    gunicorn -w 4 -b 127.0.0.1:5000 wsgi:application --daemon
"""
import os
from dotenv import load_dotenv
from app import create_app
from app.utils.scheduler import start_background_scheduler

# Load environment variables
load_dotenv()

# Create production application
application = create_app(os.getenv('FLASK_ENV', 'production'))

# Start background scheduler for radio status updates
start_background_scheduler(application)

# Gunicorn compatibility - 'app' alias
app = application
