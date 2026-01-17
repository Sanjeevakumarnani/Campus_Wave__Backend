from flask import Flask
import os
from config import config
from app.extensions import db, migrate, jwt, cors, mail

def create_app(config_name='development'):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app)
    mail.init_app(app)
    
    # Create upload folder if it doesn't exist
    upload_folder = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
    
    # Register blueprints
    from app.routes import auth, radios, suggestions, dashboard
    app.register_blueprint(auth.bp)
    app.register_blueprint(radios.bp)
    app.register_blueprint(suggestions.bp)
    app.register_blueprint(dashboard.bp)
    
    from app.routes import reviews
    app.register_blueprint(reviews.bp)
    
    # New feature blueprints
    from app.routes import categories, favorites, comments, analytics, notifications, updates, banners, live_stream, placements, marquee, live_podcasts
    app.register_blueprint(categories.bp)
    app.register_blueprint(favorites.bp)
    app.register_blueprint(comments.bp)
    app.register_blueprint(analytics.bp)
    app.register_blueprint(notifications.bp)
    app.register_blueprint(updates.bp)
    app.register_blueprint(banners.bp)
    app.register_blueprint(live_stream.bp)
    app.register_blueprint(placements.bp)
    app.register_blueprint(marquee.marquee_bp, url_prefix='/api/marquees')
    app.register_blueprint(live_podcasts.bp)
    
    from app.routes import reports
    app.register_blueprint(reports.bp)
    
    # Serve uploaded files
    from flask import send_from_directory
    @app.route('/uploads/<path:filename>')
    def serve_upload(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    # Register error handlers
    from app.errors import handlers
    handlers.register_error_handlers(app)
    
    return app
