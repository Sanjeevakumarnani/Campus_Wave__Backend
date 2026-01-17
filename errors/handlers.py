from flask import jsonify, current_app
import traceback

def register_error_handlers(app):
    """Register global error handlers for production-ready error responses"""
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'NOT_FOUND',
            'message': 'Resource not found'
        }), 404
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'success': False,
            'error': 'FORBIDDEN',
            'message': 'Access forbidden'
        }), 403
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'success': False,
            'error': 'UNAUTHORIZED',
            'message': 'Unauthorized access'
        }), 401
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': 'BAD_REQUEST',
            'message': str(error.description) if hasattr(error, 'description') else 'Bad request'
        }), 400
    
    @app.errorhandler(413)
    def request_entity_too_large(error):
        """Handle file upload size exceeded - CRITICAL for uploads"""
        max_size = app.config.get('MAX_CONTENT_LENGTH', 0) // (1024 * 1024)
        app.logger.warning(f"File upload too large - max size: {max_size}MB")
        return jsonify({
            'success': False,
            'error': 'FILE_TOO_LARGE',
            'message': f'File exceeds maximum upload size of {max_size}MB. Please upload a smaller file.'
        }), 413
    
    @app.errorhandler(415)
    def unsupported_media_type(error):
        return jsonify({
            'success': False,
            'error': 'UNSUPPORTED_MEDIA_TYPE',
            'message': 'Unsupported file type'
        }), 415
    
    @app.errorhandler(422)
    def unprocessable_entity(error):
        return jsonify({
            'success': False,
            'error': 'UNPROCESSABLE_ENTITY',
            'message': 'The request was well-formed but unable to be processed'
        }), 422
    
    @app.errorhandler(500)
    def internal_error(error):
        """Log 500 errors with full traceback for debugging"""
        app.logger.error(f"Internal Server Error: {error}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'INTERNAL_SERVER_ERROR',
            'message': 'An unexpected error occurred. Please try again or contact support.'
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Catch-all for any unhandled exceptions - NEVER show raw 500"""
        app.logger.error(f"Unhandled Exception: {e}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'UNEXPECTED_ERROR',
            'message': f'An unexpected error occurred: {str(e)}'
        }), 500

