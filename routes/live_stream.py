from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
from app.extensions import db
from app.models.live_stream import LiveStream
from app.models.live_queue import LiveQueue
from app.models.radio import Radio
from app.middleware.auth import admin_required

bp = Blueprint('live_stream', __name__, url_prefix='/api/live-stream')

@bp.route('', methods=['GET'])
def get_live_stream_status():
    """Get current live stream status and config"""
    stream = LiveStream.query.first()
    if not stream:
        # Emergency initialization if seed wasn't run
        stream = LiveStream()
        db.session.add(stream)
        db.session.commit()
    
    return jsonify(stream.to_dict())

@bp.route('/toggle', methods=['POST'])
@admin_required
def toggle_live_stream():
    """Toggle stream status between ONLINE and OFFLINE"""
    stream = LiveStream.query.first()
    if not stream:
        return jsonify({'message': 'Live stream config not found'}), 404
        
    data = request.json
    new_status = data.get('status') # 'ONLINE' or 'OFFLINE'
    
    if new_status not in ['ONLINE', 'OFFLINE']:
        return jsonify({'message': 'Invalid status'}), 400
        
    stream.status = new_status
    if new_status == 'ONLINE':
        stream.started_at = datetime.now(timezone.utc)
    else:
        stream.started_at = None
        stream.current_audio_id = None
        
    db.session.commit()
    return jsonify(stream.to_dict())

@bp.route('/config', methods=['PUT'])
@admin_required
def update_live_stream_config():
    """Update stream title and description"""
    stream = LiveStream.query.first()
    if not stream:
        return jsonify({'message': 'Live stream config not found'}), 404
        
    data = request.json
    stream.title = data.get('title', stream.title)
    stream.description = data.get('description', stream.description)
    
    db.session.commit()
    return jsonify(stream.to_dict())

@bp.route('/queue', methods=['GET'])
def get_queue():
    """Get current live stream queue"""
    items = LiveQueue.query.order_by(LiveQueue.position.asc()).all()
    return jsonify([item.to_dict() for item in items])

@bp.route('/queue', methods=['POST'])
@admin_required
def add_to_queue():
    """Add a radio audio to the live queue"""
    data = request.json
    radio_id = data.get('radio_id')
    
    if not radio_id:
        return jsonify({'message': 'radio_id is required'}), 400
        
    radio = Radio.query.get(radio_id)
    if not radio or not radio.media_url:
        return jsonify({'message': 'Radio not found or has no media'}), 404
        
    # Get last position
    last_item = LiveQueue.query.order_by(LiveQueue.position.desc()).first()
    next_pos = (last_item.position + 1) if last_item else 0
    
    item = LiveQueue(radio_id=radio_id, position=next_pos)
    db.session.add(item)
    db.session.commit()
    
    return jsonify(item.to_dict()), 201

@bp.route('/queue/<int:item_id>', methods=['DELETE'])
@admin_required
def remove_from_queue(item_id):
    """Remove an item from the queue"""
    item = LiveQueue.query.get(item_id)
    if not item:
        return jsonify({'message': 'Queue item not found'}), 404
        
    db.session.delete(item)
    db.session.commit()
    
    return jsonify({'message': 'Item removed from queue'})

@bp.route('/queue/reorder', methods=['POST'])
@admin_required
def reorder_queue():
    """Reorder the entire queue"""
    data = request.json # Expecting list of {id, position}
    if not isinstance(data, list):
        return jsonify({'message': 'Invalid data format'}), 400
        
    for entry in data:
        item = LiveQueue.query.get(entry.get('id'))
        if item:
            item.position = entry.get('position', 0)
            
    db.session.commit()
    return jsonify({'message': 'Queue reordered'})

@bp.route('/next', methods=['POST'])
@admin_required
def skip_to_next():
    """Manually skip to next item in queue"""
    stream = LiveStream.query.first()
    if not stream:
        return jsonify({'message': 'Stream config not found'}), 404
        
    # Find next item in queue
    current_item = None
    if stream.current_audio_id:
        current_item = LiveQueue.query.filter_by(radio_id=stream.current_audio_id).first()
        
    if current_item:
        next_item = LiveQueue.query.filter(LiveQueue.position > current_item.position).order_by(LiveQueue.position.asc()).first()
    else:
        next_item = LiveQueue.query.order_by(LiveQueue.position.asc()).first()
        
    if not next_item:
        # Loop back to start if at end
        next_item = LiveQueue.query.order_by(LiveQueue.position.asc()).first()
        
    if next_item:
        stream.current_audio_id = next_item.radio_id
        db.session.commit()
        return jsonify(stream.to_dict())
    else:
        return jsonify({'message': 'Queue is empty'}), 400

@bp.route('/queue/upload', methods=['POST'])
@admin_required
def upload_to_queue():
    """
    Upload audio/video file directly to the queue.
    
    HARDENED IMPLEMENTATION:
    - Comprehensive error handling (no raw 500s)
    - MIME type validation (not just extension)
    - Streaming file writes (memory safe)
    - Database transactions with rollback
    - Detailed logging for debugging
    """
    from flask_jwt_extended import get_jwt_identity
    from werkzeug.utils import secure_filename
    import os
    import traceback
    from flask import current_app
    
    # ===== CONFIGURATION =====
    ALLOWED_EXTENSIONS = {'mp3', 'mp4', 'wav', 'ogg', 'webm', 'm4a', 'aac'}
    ALLOWED_MIME_TYPES = {
        'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/x-wav', 
        'audio/ogg', 'audio/webm', 'audio/mp4', 'audio/m4a', 'audio/aac',
        'video/mp4', 'video/webm', 'video/ogg',
        'application/octet-stream'  # Android sometimes sends this
    }
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
    
    try:
        # ===== STEP 1: Validate Request Has File =====
        if 'media' not in request.files:
            current_app.logger.warning("Upload attempt with no 'media' field")
            return jsonify({
                'success': False,
                'error': 'NO_FILE',
                'message': 'No media file provided. Ensure the field name is "media".'
            }), 400
        
        media_file = request.files['media']
        title = request.form.get('title', 'Live Queue Audio')
        
        # ===== STEP 2: Validate File is Not Empty =====
        if media_file.filename == '' or media_file.filename is None:
            current_app.logger.warning("Upload attempt with empty filename")
            return jsonify({
                'success': False,
                'error': 'EMPTY_FILENAME',
                'message': 'No file selected or filename is empty.'
            }), 400
        
        # ===== STEP 3: Validate File Extension =====
        if '.' not in media_file.filename:
            return jsonify({
                'success': False,
                'error': 'NO_EXTENSION',
                'message': 'File must have an extension (e.g., .mp3, .mp4)'
            }), 400
            
        ext = media_file.filename.rsplit('.', 1)[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            current_app.logger.warning(f"Rejected file with extension: {ext}")
            return jsonify({
                'success': False,
                'error': 'INVALID_EXTENSION',
                'message': f'Invalid file type ".{ext}". Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # ===== STEP 4: Validate MIME Type =====
        content_type = media_file.content_type or 'application/octet-stream'
        if content_type not in ALLOWED_MIME_TYPES:
            current_app.logger.warning(f"Suspicious MIME type: {content_type} for file {media_file.filename}")
            # Don't reject - Android often sends wrong MIME types
            # Just log it for monitoring
        
        # ===== STEP 5: Check File Size (if Content-Length header available) =====
        content_length = request.content_length
        if content_length and content_length > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'error': 'FILE_TOO_LARGE',
                'message': f'File exceeds maximum size of {MAX_FILE_SIZE // (1024*1024)}MB'
            }), 413
        
        # ===== STEP 6: Prepare Upload Directory =====
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        try:
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder, exist_ok=True)
                current_app.logger.info(f"Created upload folder: {upload_folder}")
        except OSError as e:
            current_app.logger.error(f"Cannot create upload folder: {e}")
            return jsonify({
                'success': False,
                'error': 'SERVER_STORAGE_ERROR',
                'message': 'Server storage configuration error. Please contact admin.'
            }), 500
        
        # ===== STEP 7: Check Disk Space (Unix-like systems) =====
        try:
            import shutil
            total, used, free = shutil.disk_usage(upload_folder)
            if free < MAX_FILE_SIZE:
                current_app.logger.error(f"Low disk space: {free} bytes free")
                return jsonify({
                    'success': False,
                    'error': 'LOW_DISK_SPACE',
                    'message': 'Server storage is full. Please contact admin.'
                }), 507
        except Exception:
            pass  # Ignore on systems without disk_usage
        
        # ===== STEP 8: Generate Safe Filename & Save File =====
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        safe_original = secure_filename(media_file.filename)
        filename = f"queue_{timestamp}_{safe_original}"
        filepath = os.path.join(upload_folder, filename)
        
        try:
            # Stream write to prevent memory issues with large files
            media_file.save(filepath)
            current_app.logger.info(f"File saved: {filepath}")
        except IOError as e:
            current_app.logger.error(f"File write failed: {e}")
            return jsonify({
                'success': False,
                'error': 'FILE_WRITE_ERROR',
                'message': 'Failed to save file to server.'
            }), 500
        
        # ===== STEP 9: Verify File Was Written =====
        if not os.path.exists(filepath):
            current_app.logger.error(f"File not found after save: {filepath}")
            return jsonify({
                'success': False,
                'error': 'FILE_SAVE_VERIFICATION_FAILED',
                'message': 'File save verification failed.'
            }), 500
        
        file_size = os.path.getsize(filepath)
        current_app.logger.info(f"File size on disk: {file_size} bytes")
        
        # ===== STEP 10: Extract Duration (Safe) =====
        duration_seconds = 0
        try:
            from mutagen import File as MutagenFile
            audio = MutagenFile(filepath)
            if audio is not None and hasattr(audio, 'info') and audio.info is not None:
                duration_seconds = int(audio.info.length)
                current_app.logger.info(f"Extracted duration: {duration_seconds}s")
        except Exception as e:
            current_app.logger.warning(f"Could not extract duration (non-fatal): {e}")
            # Continue - duration is optional
        
        # ===== STEP 11: Create Database Records (Transaction) =====
        media_url = f'/uploads/{filename}'
        media_type_str = 'VIDEO' if ext in {'mp4', 'webm'} else 'AUDIO'
        
        try:
            user_id = int(get_jwt_identity())
            from app.models.radio import RadioStatus, MediaType
            
            media_type_enum = MediaType.VIDEO if media_type_str == 'VIDEO' else MediaType.AUDIO
            
            radio = Radio(
                title=title,
                description='Uploaded for 24/7 Live Radio Queue',
                media_url=media_url,
                media_type=media_type_enum,
                status=RadioStatus.COMPLETED,
                created_by=user_id,
                start_time=datetime.now(),
                end_time=datetime.now(),
                duration=duration_seconds
            )
            db.session.add(radio)
            db.session.flush()  # Get radio.id without committing
            
            # Add to queue
            last_item = LiveQueue.query.order_by(LiveQueue.position.desc()).first()
            next_pos = (last_item.position + 1) if last_item else 0
            
            queue_item = LiveQueue(radio_id=radio.id, position=next_pos)
            db.session.add(queue_item)
            
            db.session.commit()
            current_app.logger.info(f"Database records created: Radio ID={radio.id}, Queue ID={queue_item.id}")
            
        except Exception as db_error:
            db.session.rollback()
            current_app.logger.error(f"Database error: {db_error}\n{traceback.format_exc()}")
            
            # Clean up the uploaded file since DB failed
            try:
                os.remove(filepath)
                current_app.logger.info(f"Cleaned up file after DB failure: {filepath}")
            except:
                pass
            
            return jsonify({
                'success': False,
                'error': 'DATABASE_ERROR',
                'message': 'Failed to save to database. File upload was rolled back.'
            }), 500
        
        # ===== STEP 12: Success Response =====
        return jsonify({
            'success': True,
            'message': 'Media uploaded and added to queue',
            'queue_item': queue_item.to_dict(),
            'radio': radio.to_dict(),
            'file_size': file_size,
            'duration': duration_seconds
        }), 201
        
    except Exception as e:
        # ===== CATCH-ALL: Log and Return Graceful Error =====
        current_app.logger.error(f"Unexpected upload error: {e}\n{traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': 'UNEXPECTED_ERROR',
            'message': f'An unexpected error occurred: {str(e)}'
        }), 500


@bp.route('/heartbeat', methods=['POST'])
def listener_heartbeat():
    """Send heartbeat to indicate listener is active"""
    from app.models.radio_listener import RadioListener
    from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
    import uuid
    
    data = request.json or {}
    session_id = data.get('session_id')
    
    # Generate new session if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
    
    # Try to get user_id from JWT if available
    user_id = None
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity:
            user_id = int(identity)
    except:
        pass
    
    # Get or create listener entry
    listener = RadioListener.query.filter_by(session_id=session_id).first()
    if not listener:
        listener = RadioListener(
            session_id=session_id,
            user_id=user_id,
            ip_address=request.remote_addr,
            device_info=request.headers.get('User-Agent', '')[:255]
        )
        db.session.add(listener)
    else:
        listener.last_heartbeat = datetime.now()
        if user_id and not listener.user_id:
            listener.user_id = user_id
    
    db.session.commit()
    
    # Get current stream info
    stream = LiveStream.query.first()
    listener_count = RadioListener.get_active_count()
    
    return jsonify({
        'session_id': session_id,
        'listener_count': listener_count,
        'stream_status': stream.status if stream else 'OFFLINE',
        'current_audio_id': stream.current_audio_id if stream else None
    })


@bp.route('/listeners', methods=['GET'])
def get_listener_count():
    """Get current listener count"""
    from app.models.radio_listener import RadioListener
    
    count = RadioListener.get_active_count()
    
    return jsonify({
        'count': count,
        'active_timeout_minutes': 5
    })


@bp.route('/listeners/cleanup', methods=['POST'])
@admin_required
def cleanup_stale_listeners():
    """Manually cleanup stale listener entries"""
    from app.models.radio_listener import RadioListener
    
    removed = RadioListener.cleanup_stale()
    
    return jsonify({
        'message': f'Removed {removed} stale listeners',
        'current_count': RadioListener.get_active_count()
    })
