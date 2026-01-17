from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app.extensions import db
from app.models.radio import Radio, RadioStatus, MediaType, HostStatus
from app.models.user import User
from app.models.radio_subscription import RadioSubscription
from app.models.notification import Notification
from app.models.favorite import Favorite
from app.middleware.auth import admin_required
from app.utils.upload import save_upload, allowed_file

bp = Blueprint('radios', __name__, url_prefix='/api/radios')


# ==================== Server Time Sync ====================

@bp.route('/server-time', methods=['GET'])
def get_server_time():
    """Get current server time for client synchronization"""
    now = datetime.now()
    return jsonify({
        'server_time': now.isoformat(),
        'timestamp': int(now.timestamp() * 1000)  # Unix timestamp in milliseconds
    }), 200

@bp.route('', methods=['GET'])
def get_radios():
    """Get all radios with optional filtering and search"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    # Filter parameters
    status = request.args.get('status', type=str)
    category_id = request.args.get('category_id', type=int)
    search = request.args.get('search', type=str)
    date_from = request.args.get('date_from', type=str)
    date_to = request.args.get('date_to', type=str)
    sort_by = request.args.get('sort_by', 'start_time', type=str)
    sort_order = request.args.get('sort_order', 'desc', type=str)
    
    query = Radio.query
    
    # Filter by status
    if status:
        try:
            status_enum = RadioStatus[status.upper()]
            query = query.filter_by(status=status_enum)
        except KeyError:
            pass
    
    # Filter by category
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    # Search by title or description
    if search:
        search_term = f'%{search}%'
        query = query.filter(
            db.or_(
                Radio.title.ilike(search_term),
                Radio.description.ilike(search_term)
            )
        )
    
    # Date range filter
    if date_from:
        try:
            from_date = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
            query = query.filter(Radio.start_time >= from_date)
        except:
            pass
    
    if date_to:
        try:
            to_date = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
            query = query.filter(Radio.end_time <= to_date)
        except:
            pass
    
    # Sorting
    sort_column = getattr(Radio, sort_by, Radio.start_time)
    if sort_order == 'asc':
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    
    return jsonify({
        'radios': [radio.to_dict() for radio in pagination.items],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    }), 200

@bp.route('/live', methods=['GET'])
def get_live_radios():
    """Get currently live radios"""
    now = datetime.now()  # Use local time to match Android app
    radios = Radio.query.filter(
        Radio.status == RadioStatus.LIVE,
        # Remove strict start_time check so early starts work
        Radio.end_time >= now
    ).all()
    
    return jsonify([radio.to_dict() for radio in radios]), 200

@bp.route('/upcoming', methods=['GET'])
@jwt_required(optional=True)
def get_upcoming_radios():
    """Get upcoming radios"""
    user_id = get_jwt_identity()
    user_id = int(user_id) if user_id else None
    
    now = datetime.now()  # Use local time to match Android app
    radios = Radio.query.filter(
        Radio.status == RadioStatus.UPCOMING,
        # Allow radios that have started but not yet hosted (late start) to appear
        Radio.end_time > now
    ).order_by(Radio.start_time).all()
    
    # Get user subscriptions if logged in
    subscribed_ids = set()
    if user_id:
        subscriptions = RadioSubscription.query.filter_by(user_id=user_id).all()
        subscribed_ids = {sub.radio_id for sub in subscriptions}
    
    result = []
    now = datetime.now()
    for radio in radios:
        data = radio.to_dict()
        data['is_subscribed'] = radio.id in subscribed_ids
        # Add seconds until start for countdown timer
        if radio.start_time > now:
            data['seconds_until_start'] = int((radio.start_time - now).total_seconds())
        else:
            data['seconds_until_start'] = 0
        result.append(data)
    
    return jsonify(result), 200

@bp.route('/missed', methods=['GET'])
def get_missed_radios():
    """Get missed/completed radios (radios that have ended)"""
    now = datetime.now()  # Use local time to match Android app
    radios = Radio.query.filter(
        Radio.end_time < now
    ).order_by(Radio.end_time.desc()).limit(50).all()
    
    # Also update status to COMPLETED if not already
    for radio in radios:
        if radio.status != RadioStatus.COMPLETED:
            radio.status = RadioStatus.COMPLETED
    db.session.commit()
    
    return jsonify([radio.to_dict() for radio in radios]), 200

@bp.route('/<int:radio_id>', methods=['GET'])
def get_radio(radio_id):
    """Get single radio session details"""
    radio = Radio.query.get(radio_id)
    if not radio:
        return jsonify({'error': 'Radio session not found'}), 404
    
    return jsonify(radio.to_dict()), 200

@bp.route('', methods=['POST'])
@admin_required
def create_radio():
    """Create new radio (admin only)"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # Validate required fields
    required = ['title', 'start_time', 'end_time']
    if not all(field in data for field in required):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Parse datetime strings
    try:
        start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return jsonify({'error': 'Invalid datetime format'}), 400
    
    # Create radio
    radio = Radio(
        title=data['title'],
        description=data.get('description', ''),
        location=data.get('location', ''),
        # media_url=data.get('media_url', ''), # SECURITY: Do not allow direct media_url setting
        start_time=start_time,
        end_time=end_time,
        status=RadioStatus[data.get('status', 'UPCOMING').upper()] if data.get('status') else RadioStatus.UPCOMING,
        created_by=user_id
    )
    
    db.session.add(radio)
    db.session.commit()
    
    return jsonify(radio.to_dict()), 201

@bp.route('/<int:radio_id>', methods=['PUT'])
@admin_required
def update_radio(radio_id):
    """Update radio session (admin only)"""
    radio = Radio.query.get(radio_id)
    if not radio:
        return jsonify({'error': 'Radio session not found'}), 404
    
    data = request.get_json()
    
    # Update fields
    if 'title' in data:
        radio.title = data['title']
    if 'description' in data:
        radio.description = data['description']
    if 'media_url' in data:
        radio.media_url = data['media_url']
    if 'location' in data:
        radio.location = data['location']
    if 'start_time' in data:
        radio.start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
    if 'end_time' in data:
        radio.end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
    if 'status' in data:
        radio.status = RadioStatus[data['status'].upper()]
    
    db.session.commit()
    
    return jsonify(radio.to_dict()), 200

@bp.route('/<int:radio_id>', methods=['DELETE'])
@admin_required
def delete_radio(radio_id):
    """Delete radio session (admin only)"""
    try:
        radio = Radio.query.get(radio_id)
        if not radio:
            return jsonify({'error': 'Radio session not found'}), 404
        
        radio_id_val = radio.id
        
        # NOTE: Raw SQL used intentionally to avoid legacy ORM cascade issues
        # Clean up ALL dependent records using RAW SQL to avoid ORM issues/cascades
        db.session.execute(db.text('DELETE FROM favorites WHERE radio_id = :rid'), {'rid': radio_id_val})
        db.session.execute(db.text('DELETE FROM radio_participants WHERE radio_id = :rid'), {'rid': radio_id_val})
        db.session.execute(db.text('DELETE FROM radio_subscriptions WHERE radio_id = :rid'), {'rid': radio_id_val})
        
        # Optional tables - wrap in try/pass to be safe, but use raw SQL
        try:
            db.session.execute(db.text('DELETE FROM live_queue WHERE radio_id = :rid'), {'rid': radio_id_val})
        except:
            pass
            
        try:
            db.session.execute(db.text('DELETE FROM reviews WHERE radio_id = :rid'), {'rid': radio_id_val})
        except:
            pass
            
        try:
            db.session.execute(db.text('DELETE FROM report WHERE session_id = :rid'), {'rid': radio_id_val})
        except:
            pass
        
        # Now safe to delete radio using RAW SQL
        db.session.execute(db.text('DELETE FROM radios WHERE id = :rid'), {'rid': radio_id_val})
        db.session.commit()
        
        return jsonify({'message': 'Radio session deleted successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': 'Delete radio failed',
            'details': str(e)
        }), 500

@bp.route('/<int:radio_id>/upload-banner', methods=['POST'])
@admin_required
def upload_banner(radio_id):
    """Upload radio banner image (admin only)"""
    radio = Radio.query.get(radio_id)
    if not radio:
        return jsonify({'error': 'Radio session not found'}), 404
    
    if 'banner' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['banner']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    # Save file
    filename = save_upload(file)
    if not filename:
        return jsonify({'error': 'Failed to save file'}), 500
    
    # Update radio
    radio.banner_image = filename
    db.session.commit()
    
    return jsonify({
        'message': 'Banner uploaded successfully',
        'banner_image': f'/uploads/{filename}',
        'banner_url': f'/uploads/{filename}'
    }), 200

@bp.route('/<int:radio_id>/upload-media', methods=['POST'])
@admin_required
def upload_media(radio_id):
    """Upload radio audio/media file (admin only)"""
    radio = Radio.query.get(radio_id)
    if not radio:
        return jsonify({'error': 'Radio session not found'}), 404
    
    if 'media' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['media']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400
    
    # Save file
    filename = save_upload(file)
    if not filename:
        return jsonify({'error': 'Failed to save file'}), 500
    
    # Update radio
    radio.media_url = f'/uploads/{filename}'
    db.session.commit()
    
    return jsonify({
        'message': 'Media uploaded successfully',
        'media_url': radio.media_url
    }), 200


@bp.route('/<int:radio_id>/subscribe', methods=['POST'])
@jwt_required()
def toggle_subscription(radio_id):
    """Toggle radio subscription"""
    user_id = int(get_jwt_identity())
    radio = Radio.query.get(radio_id)
    
    if not radio:
        return jsonify({'error': 'Radio session not found'}), 404
        
    subscription = RadioSubscription.query.filter_by(
        user_id=user_id,
        radio_id=radio_id
    ).first()
    
    if subscription:
        db.session.delete(subscription)
        message = "Unsubscribed from radio session"
        is_subscribed = False
    else:
        subscription = RadioSubscription(user_id=user_id, radio_id=radio_id)
        db.session.add(subscription)
        message = "Subscribed to radio session"
        is_subscribed = True
        
    db.session.commit()
    
    return jsonify({
        'message': message,
        'is_subscribed': is_subscribed
    }), 200

# ==================== Live Hosting Endpoints ====================

@bp.route('/<int:radio_id>/start-hosting', methods=['POST'])
@admin_required
def start_hosting(radio_id):
    """Start hosting a radio session (admin only)"""
    user_id = int(get_jwt_identity())
    radio = Radio.query.get(radio_id)
    
    if not radio:
        return jsonify({'error': 'Radio session not found'}), 404
    
    # Check if radio is ready to be hosted (time has arrived or is upcoming)
    now = datetime.now()  # Use local time to match Android app
    if radio.start_time > now:
        # Allow hosting up to 5 minutes before start time
        time_diff = (radio.start_time - now).total_seconds()
        if time_diff > 300:  # More than 5 minutes before
            return jsonify({'error': 'Radio session cannot be hosted yet. Wait until closer to start time.'}), 400
    
        if time_diff > 300:  # More than 5 minutes before
            return jsonify({'error': 'Radio session cannot be hosted yet. Wait until closer to start time.'}), 400
    
    # CRITICAL: Logic Ownership - Cannot go LIVE without media
    if not radio.media_url:
        return jsonify({'error': 'Cannot start hosting: No media file uploaded for this radio.'}), 400

    # Get media type from request
    data = request.get_json() or {}
    media_type_str = data.get('media_type', 'AUDIO').upper()
    
    try:
        media_type = MediaType[media_type_str]
    except KeyError:
        return jsonify({'error': 'Invalid media type. Use AUDIO or VIDEO.'}), 400
    
    # Update radio
    radio.status = RadioStatus.LIVE
    radio.host_status = HostStatus.HOSTING
    radio.media_type = media_type
    radio.hosted_by = user_id
    radio.stream_started_at = datetime.now()  # Use local time
    
    db.session.commit()
    
    # Notify subscribers
    subscribers = RadioSubscription.query.filter_by(radio_id=radio_id).all()
    for sub in subscribers:
        notification = Notification(
            user_id=sub.user_id,
            title=f"Radio Live: {radio.title}",
            message=f"{radio.title} is now live! Join the {media_type_str.lower()} stream.",
            type="RADIO_LIVE",
            related_id=radio.id
        )
        db.session.add(notification)
    
    if subscribers:
        db.session.commit()
    
    # CRITICAL: Update Global LiveStream for Student Player
    from app.models.live_stream import LiveStream
    stream = LiveStream.query.first()
    if not stream:
        stream = LiveStream(status='ONLINE', started_at=datetime.now())
        db.session.add(stream)
    
    stream.current_audio_id = radio.id
    stream.status = 'ONLINE'
    stream.started_at = datetime.now()
    stream.title = radio.title
    stream.description = radio.description
    db.session.commit()

    
    return jsonify({
        'message': f'Radio session is now live as {media_type_str}',
        'radio': radio.to_dict()
    }), 200


@bp.route('/<int:radio_id>/pause-hosting', methods=['PUT'])
@admin_required
def pause_hosting(radio_id):
    """Pause a live radio (admin only)"""
    radio = Radio.query.get(radio_id)
    
    if not radio:
        return jsonify({'error': 'Radio session not found'}), 404
    
    if radio.host_status != HostStatus.HOSTING:
        return jsonify({'error': 'Radio session is not currently being hosted'}), 400
    
    radio.host_status = HostStatus.PAUSED
    db.session.commit()
    
    return jsonify({
        'message': 'Radio session paused',
        'radio': radio.to_dict()
    }), 200


@bp.route('/<int:radio_id>/resume-hosting', methods=['PUT'])
@admin_required
def resume_hosting(radio_id):
    """Resume a paused radio (admin only)"""
    radio = Radio.query.get(radio_id)
    
    if not radio:
        return jsonify({'error': 'Radio session not found'}), 404
    
    if radio.host_status != HostStatus.PAUSED:
        return jsonify({'error': 'Radio session is not paused'}), 400
    
    radio.host_status = HostStatus.HOSTING
    db.session.commit()
    
    return jsonify({
        'message': 'Radio session resumed',
        'radio': radio.to_dict()
    }), 200


@bp.route('/<int:radio_id>/end-hosting', methods=['PUT'])
@admin_required
def end_hosting(radio_id):
    """End a live radio (admin only)"""
    radio = Radio.query.get(radio_id)
    
    if not radio:
        return jsonify({'error': 'Radio session not found'}), 404
    
    if radio.host_status not in [HostStatus.HOSTING, HostStatus.PAUSED]:
        return jsonify({'error': 'Radio session is not being hosted'}), 400
    
    radio.status = RadioStatus.COMPLETED
    radio.host_status = HostStatus.ENDED
    radio.end_time = datetime.now()  # Use local time for immediate sync
    
    db.session.commit()
    
    return jsonify({
        'message': 'Radio session ended successfully',
        'radio': radio.to_dict()
    }), 200


@bp.route('/<int:radio_id>/stream-info', methods=['GET'])
def get_stream_info(radio_id):
    """Get stream info for students to view"""
    radio = Radio.query.get(radio_id)
    
    if not radio:
        return jsonify({'error': 'Radio session not found'}), 404
    
    return jsonify({
        'radio_id': radio.id,
        'title': radio.title,
        'status': radio.status.value,
        'host_status': radio.host_status.value if radio.host_status else 'NOT_STARTED',
        'media_type': radio.media_type.value if radio.media_type else 'NONE',
        'media_url': radio.media_url,
        'is_live': radio.status == RadioStatus.LIVE and radio.host_status == HostStatus.HOSTING,
        'is_paused': radio.host_status == HostStatus.PAUSED,
        'end_time': radio.end_time.isoformat() if radio.end_time else None,
        'duration': radio.duration or 0
    }), 200


@bp.route('/<int:radio_id>/mark-completed', methods=['POST'])
def mark_radio_completed(radio_id):
    """Mark a radio event as completed (called by client when end time is reached)"""
    radio = Radio.query.get(radio_id)
    
    if not radio:
        return jsonify({'error': 'Radio session not found'}), 404
    
    # Only mark as completed if currently live or hosting
    if radio.status == RadioStatus.LIVE or radio.host_status in [HostStatus.HOSTING, HostStatus.PAUSED]:
        radio.status = RadioStatus.COMPLETED
        radio.host_status = HostStatus.ENDED
        
        # Update global live stream status
        from app.models.live_stream import LiveStream
        stream = LiveStream.query.first()
        if stream and stream.current_audio_id == radio.id:
            stream.status = 'OFFLINE'
        
        db.session.commit()
        
        return jsonify({
            'message': 'Radio marked as completed',
            'radio': radio.to_dict()
        }), 200
    
    return jsonify({
        'message': 'Radio is not currently active',
        'radio': radio.to_dict()
    }), 200

