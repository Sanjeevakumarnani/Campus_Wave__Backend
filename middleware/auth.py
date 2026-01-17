from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models.user import User, UserRole

def token_required(fn):
    """Decorator to require authentication and pass current_user"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        try:
            user_id = int(get_jwt_identity())
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            return fn(user, *args, **kwargs)
        except Exception as e:
            return jsonify({'error': 'Invalid token'}), 401
    return wrapper

def admin_required(fn):
    """Decorator to require admin role"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())  # Convert string to int
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if user.role not in [UserRole.ADMIN, UserRole.MAIN_ADMIN]:
            return jsonify({'error': 'Admin access required'}), 403
        
        print(f"[DEBUG] admin_required calling {fn.__name__} with args={args}, kwargs={kwargs}")
        return fn(*args, **kwargs)
    return wrapper

def student_required(fn):
    """Decorator to require student role"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = int(get_jwt_identity())  # Convert string to int
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if user.role != UserRole.STUDENT:
            return jsonify({'error': 'Student access required'}), 403
        
        return fn(*args, **kwargs)
    return wrapper
