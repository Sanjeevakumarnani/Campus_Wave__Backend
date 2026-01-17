from flask import Blueprint, jsonify
from datetime import datetime
from sqlalchemy import func, distinct
from app.extensions import db
from app.models.radio import Radio, RadioStatus, radio_participants
from app.models.radio_suggestion import RadioSuggestion, SuggestionStatus
from app.models.user import User, UserRole
from app.models.admin_request import AdminRequest, RequestStatus
from app.middleware.auth import admin_required
from flask_jwt_extended import get_jwt_identity

bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')

@bp.route('/stats', methods=['GET'])
@admin_required
def get_stats():
    """Get dashboard statistics (admin only)"""
    
    # Total radios
    total_radios = Radio.query.count()
    
    # Active participants (participants in live radios)
    active_participants = db.session.query(
        func.count(distinct(radio_participants.c.user_id))
    ).join(Radio).filter(Radio.status == RadioStatus.LIVE).scalar() or 0
    
    # Pending suggestions
    pending_suggestions = RadioSuggestion.query.filter_by(
        status=SuggestionStatus.PENDING
    ).count()
    
    # Get current user for role and extra stats
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    pending_admin_requests = 0
    if user and user.role == UserRole.MAIN_ADMIN:
        pending_admin_requests = AdminRequest.query.filter_by(
            status=RequestStatus.PENDING
        ).count()
    
    return jsonify({
        'total_radios': total_radios,
        'active_participants': active_participants,
        'pending_suggestions': pending_suggestions,
        'pending_admin_requests': pending_admin_requests,
        'role': user.role.value if user else 'ADMIN'
    }), 200

@bp.route('/analytics/radios', methods=['GET'])
@admin_required
def get_radio_analytics():
    """Get radio breakdown by status (admin only)"""
    
    stats = {}
    for status in RadioStatus:
        count = Radio.query.filter_by(status=status).count()
        stats[status.value.lower()] = count
    
    return jsonify(stats), 200

@bp.route('/analytics/participation', methods=['GET'])
@admin_required
def get_participation_analytics():
    """Get participation trends (admin only)"""
    
    # Get total participants per radio
    result = db.session.query(
        Radio.title,
        Radio.status,
        func.count(radio_participants.c.user_id).label('participant_count')
    ).outerjoin(radio_participants).group_by(Radio.id).all()
    
    participation_data = []
    for title, status, count in result:
        participation_data.append({
            'radio_title': title,
            'status': status.value,
            'participant_count': count
        })
    
    return jsonify(participation_data), 200
