"""
API routes for Live Podcast feature.

Admin can schedule, start, and stop live podcast sessions.
Students can view current live status and join live podcasts.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app.extensions import db
from app.models.live_podcast import LivePodcast, PodcastStatus
from app.models.user import User, UserRole
from app.middleware.auth import admin_required

bp = Blueprint('live_podcasts', __name__, url_prefix='/api/live-podcasts')


@bp.route('/schedule', methods=['POST'])
@admin_required
def schedule_podcast(current_user_id):
    """Schedule a new live podcast (admin only)"""
    data = request.get_json()
    
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    scheduled_start_time = data.get('scheduled_start_time')
    
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    
    # Parse scheduled start time
    scheduled_dt = None
    if scheduled_start_time:
        try:
            scheduled_dt = datetime.fromisoformat(scheduled_start_time.replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid scheduled_start_time format. Use ISO 8601'}), 400
    
    # Check if there's already a live or scheduled podcast
    existing = LivePodcast.query.filter(
        LivePodcast.status.in_([PodcastStatus.LIVE, PodcastStatus.SCHEDULED])
    ).first()
    
    if existing:
        return jsonify({
            'error': 'Cannot schedule. There is already a live or scheduled podcast',
            'existing_podcast': existing.to_dict()
        }), 409
    
    podcast = LivePodcast(
        admin_id=current_user_id,
        title=title,
        description=description,
        scheduled_start_time=scheduled_dt,
        status=PodcastStatus.SCHEDULED
    )
    
    db.session.add(podcast)
    db.session.commit()
    
    return jsonify({
        'message': 'Podcast scheduled successfully',
        'podcast': podcast.to_dict()
    }), 201


@bp.route('/<int:podcast_id>/start', methods=['POST'])
@admin_required
def start_podcast(current_user_id, podcast_id):
    """Start a scheduled podcast (admin only)"""
    podcast = LivePodcast.query.get(podcast_id)
    
    if not podcast:
        return jsonify({'error': 'Podcast not found'}), 404
    
    if podcast.admin_id != current_user_id:
        return jsonify({'error': 'Unauthorized. You can only start your own podcasts'}), 403
    
    if podcast.status == PodcastStatus.LIVE:
        return jsonify({'error': 'Podcast is already live'}), 400
    
    if podcast.status == PodcastStatus.ENDED:
        return jsonify({'error': 'Cannot start an ended podcast'}), 400
    
    # Check if another podcast is live
    other_live = LivePodcast.query.filter(
        LivePodcast.id != podcast_id,
        LivePodcast.status == PodcastStatus.LIVE
    ).first()
    
    if other_live:
        return jsonify({
            'error': 'Another podcast is already live. Only one live podcast at a time',
            'live_podcast': other_live.to_dict()
        }), 409
    
    # Start the podcast
    podcast.status = PodcastStatus.LIVE
    podcast.actual_start_time = datetime.utcnow()
    
    # Generate stream URL (in production, this would be a real WebRTC/HLS URL)
    # For now, using a placeholder
    podcast.stream_url = f'/api/live-podcasts/{podcast_id}/stream'
    
    db.session.commit()
    
    return jsonify({
        'message': 'Podcast started successfully',
        'podcast': podcast.to_dict()
    }), 200


@bp.route('/<int:podcast_id>/stop', methods=['POST'])
@admin_required
def stop_podcast(current_user_id, podcast_id):
    """Stop a live podcast (admin only)"""
    podcast = LivePodcast.query.get(podcast_id)
    
    if not podcast:
        return jsonify({'error': 'Podcast not found'}), 404
    
    if podcast.admin_id != current_user_id:
        return jsonify({'error': 'Unauthorized. You can only stop your own podcasts'}), 403
    
    if podcast.status != PodcastStatus.LIVE:
        return jsonify({'error': 'Podcast is not currently live'}), 400
    
    # Stop the podcast
    podcast.status = PodcastStatus.ENDED
    podcast.end_time = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({
        'message': 'Podcast stopped successfully',
        'podcast': podcast.to_dict()
    }), 200


@bp.route('/current', methods=['GET'])
def get_current_podcast():
    """Get current live podcast status (public)"""
    live_podcast = LivePodcast.query.filter_by(status=PodcastStatus.LIVE).first()
    
    if not live_podcast:
        return jsonify({
            'is_live': False,
            'podcast': None
        }), 200
    
    return jsonify({
        'is_live': True,
        'podcast': live_podcast.to_dict()
    }), 200


@bp.route('', methods=['GET'])
@jwt_required()
def get_podcasts():
    """List all podcasts (admin: all, students: live/past only)"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    status_filter = request.args.get('status')  # Optional: SCHEDULED, LIVE, ENDED
    
    query = LivePodcast.query
    
    # Students can only see LIVE and ENDED
    if user.role != UserRole.ADMIN:
        query = query.filter(LivePodcast.status.in_([PodcastStatus.LIVE, PodcastStatus.ENDED]))
    
    # Apply status filter if provided
    if status_filter:
        try:
            status_enum = PodcastStatus[status_filter.upper()]
            query = query.filter_by(status=status_enum)
        except KeyError:
            return jsonify({'error': 'Invalid status value'}), 400
    
    pagination = query.order_by(LivePodcast.created_at.desc()).paginate(
        page=page, per_page=limit, error_out=False
    )
    
    return jsonify({
        'podcasts': [p.to_dict() for p in pagination.items],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    }), 200


@bp.route('/<int:podcast_id>', methods=['DELETE'])
@admin_required
def delete_podcast(current_user_id, podcast_id):
    """Delete a scheduled podcast (admin only)"""
    podcast = LivePodcast.query.get(podcast_id)
    
    if not podcast:
        return jsonify({'error': 'Podcast not found'}), 404
    
    if podcast.admin_id != current_user_id:
        return jsonify({'error': 'Unauthorized. You can only delete your own podcasts'}), 403
    
    if podcast.status == PodcastStatus.LIVE:
        return jsonify({'error': 'Cannot delete a live podcast. Stop it first'}), 400
    
    db.session.delete(podcast)
    db.session.commit()
    
    return jsonify({'message': 'Podcast deleted successfully'}), 200
