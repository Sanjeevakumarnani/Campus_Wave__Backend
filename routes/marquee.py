from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.models import Marquee
from app.extensions import db
from app.middleware.auth import admin_required

marquee_bp = Blueprint('marquee', __name__)

@marquee_bp.before_request
def log_request():
    print(f"[MARQUEE] === Incoming {request.method} {request.path} ===")
    print(f"[MARQUEE] Headers: {dict(request.headers)}")
    print(f"[MARQUEE] Body: {request.get_data(as_text=True)}")


@marquee_bp.route('/', methods=['POST'])
@admin_required
def create_or_update_marquee():
    """Create or update the active marquee"""
    try:
        current_user_id = int(get_jwt_identity())
        data = request.get_json()
        print(f"[MARQUEE] Received data: {data}")
        print(f"[MARQUEE] Current user ID: {current_user_id}")
        
        if not data or 'text' not in data:
            return jsonify({'error': 'Marquee text is required'}), 400
        
        # Deactivate all existing marquees
        Marquee.query.update({'is_active': False})
        
        # Create new marquee
        marquee = Marquee(
            text=data['text'],
            text_color=data.get('text_color', '#FFFFFF'),
            bg_color=data.get('bg_color', '#4F46E5'),
            speed=data.get('speed', 'medium'),
            is_active=True
        )
        
        print(f"[MARQUEE] Created marquee object: {marquee.text}")
        db.session.add(marquee)
        db.session.commit()
        print(f"[MARQUEE] Successfully saved to database")
        
        return jsonify(marquee.to_dict()), 201
        
    except Exception as e:
        print(f"[MARQUEE ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        db.session.rollback()
        return jsonify({'error': f'{type(e).__name__}: {str(e)}'}), 500

@marquee_bp.route('/active', methods=['GET'])
def get_active_marquee():
    """Get the currently active marquee"""
    try:
        marquee = Marquee.query.filter_by(is_active=True).first()
        
        if not marquee:
            return jsonify({'message': 'No active marquee'}), 404
        
        return jsonify(marquee.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
