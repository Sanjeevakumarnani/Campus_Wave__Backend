from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app.extensions import db
from app.models.radio_suggestion import RadioSuggestion, SuggestionStatus
from app.models.radio import Radio, RadioStatus
from app.models.user import User
from app.models.notification import Notification
from app.middleware.auth import admin_required, student_required
from app.utils.email import send_suggestion_approved_email
from app.models.category import Category

bp = Blueprint('suggestions', __name__, url_prefix='/api/suggestions')

@bp.route('', methods=['GET'])
@admin_required
def get_suggestions():
    """Get all suggestions (admin only)"""
    status = request.args.get('status', type=str)
    
    query = RadioSuggestion.query
    
    # Filter by status if provided
    if status:
        try:
            status_enum = SuggestionStatus[status.upper()]
            query = query.filter_by(status=status_enum)
        except KeyError:
            pass
    
    suggestions = query.order_by(RadioSuggestion.created_at.desc()).all()
    
    # Include student details
    result = []
    for suggestion in suggestions:
        data = suggestion.to_dict()
        student = User.query.get(suggestion.suggested_by)
        if student:
            data['student_name'] = student.name
            data['student_email'] = student.email
        result.append(data)
    
    return jsonify(result), 200

@bp.route('/pending', methods=['GET'])
@admin_required
def get_pending_suggestions():
    """Get pending suggestions (admin only)"""
    suggestions = RadioSuggestion.query.filter_by(status=SuggestionStatus.PENDING).all()
    
    result = []
    for suggestion in suggestions:
        data = suggestion.to_dict()
        student = User.query.get(suggestion.suggested_by)
        if student:
            data['student_name'] = student.name
            data['student_email'] = student.email
        result.append(data)
    
    return jsonify(result), 200

@bp.route('', methods=['POST'])
@jwt_required()
def create_suggestion():
    """Create new suggestion (any authenticated user)"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # Validate required fields
    if not data or not data.get('radio_title'):
        return jsonify({'error': 'Radio title is required'}), 400
    
    # Create suggestion
    suggestion = RadioSuggestion(
        radio_title=data['radio_title'],
        description=data.get('description', ''),
        category=data.get('category'),
        suggested_by=user_id,
        status=SuggestionStatus.PENDING
    )
    
    db.session.add(suggestion)
    db.session.commit()
    
    return jsonify(suggestion.to_dict()), 201

@bp.route('/<int:suggestion_id>/approve', methods=['PUT'])
@admin_required
def approve_suggestion(suggestion_id):
    """Approve suggestion and create event (admin only)"""
    user_id = int(get_jwt_identity())
    suggestion = RadioSuggestion.query.get(suggestion_id)
    
    if not suggestion:
        return jsonify({'error': 'Suggestion not found'}), 404
    
    if suggestion.status != SuggestionStatus.PENDING:
        return jsonify({'error': 'Suggestion already reviewed'}), 400
    
    # Update suggestion status
    suggestion.status = SuggestionStatus.APPROVED
    suggestion.reviewed_by = user_id
    suggestion.reviewed_at = datetime.utcnow()
    
    # Create radio session from suggestion
    # Set default times (can be updated later by admin)
    default_start = datetime.utcnow()
    default_end = datetime.utcnow()
    
    radio = Radio(
        title=suggestion.radio_title,
        description=suggestion.description,
        start_time=default_start,
        end_time=default_end,
        status=RadioStatus.DRAFT,
        created_by=user_id
    )
    
    # Handle category lookup and assignment
    if suggestion.category:
        category = Category.query.filter_by(name=suggestion.category).first()
        if category:
            radio.category_id = category.id
    
    db.session.add(radio)
    


    # Notify student
    notification = Notification(
        user_id=suggestion.suggested_by,
        title="Suggestion Accepted 🎉",
        message=f"Your suggestion '{suggestion.radio_title}' has been reviewed and accepted by the admin. Thank you for your valuable feedback!",
        type="SUGGESTION_APPROVED",
        related_id=radio.id
    )
    db.session.add(notification)
    
    # Send email notification
    student = User.query.get(suggestion.suggested_by)
    if student:
        send_suggestion_approved_email(student.email, student.name, suggestion.radio_title)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Suggestion approved and radio session created',
        'suggestion': suggestion.to_dict(),
        'radio_id': radio.id
    }), 200

@bp.route('/<int:suggestion_id>/reject', methods=['PUT'])
@admin_required
def reject_suggestion(suggestion_id):
    """Reject suggestion (admin only)"""
    user_id = int(get_jwt_identity())
    suggestion = RadioSuggestion.query.get(suggestion_id)
    
    if not suggestion:
        return jsonify({'error': 'Suggestion not found'}), 404
    
    if suggestion.status != SuggestionStatus.PENDING:
        return jsonify({'error': 'Suggestion already reviewed'}), 400
    
    # Update suggestion status
    suggestion.status = SuggestionStatus.REJECTED
    suggestion.reviewed_by = user_id
    suggestion.reviewed_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'message': 'Suggestion rejected',
        'suggestion': suggestion.to_dict()
    }), 200
