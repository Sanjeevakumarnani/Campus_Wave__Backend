from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app.extensions import db
from app.models.notification import Notification
from app.models.global_notification import GlobalNotification, UserNotificationStatus
from app.models.user import User, UserRole
from app.middleware.auth import admin_required
from app.utils.upload import save_upload, allowed_file
import os

bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')


@bp.route('/broadcast', methods=['POST'])
@admin_required
def broadcast_notification(current_user_id):
    """Send a global notification to all users (admin only)"""
    data = request.get_json()
    
    title = data.get('title', '').strip()
    message = data.get('message', '').strip()
    image_url = data.get('image_url', '').strip()
    
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    # Create global notification
    global_notif = GlobalNotification(
        title=title,
        message=message,
        image_url=image_url if image_url else None,
        created_by=current_user_id
    )
    
    db.session.add(global_notif)
    db.session.commit()
    
    # Create status entries for all users
    all_users = User.query.all()
    for user in all_users:
        status = UserNotificationStatus(
            notification_id=global_notif.id,
            user_id=user.id,
            is_read=False
        )
        db.session.add(status)
    
    db.session.commit()
    
    return jsonify({
        'message': f'Notification broadcast to {len(all_users)} users',
        'notification': global_notif.to_dict(current_user_id)
    }), 201


@bp.route('/upload-image', methods=['POST'])
@admin_required
def upload_notification_image(current_user_id):
    """Upload image for notification (admin only)"""
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename, allowed_extensions=['png', 'jpg', 'jpeg', 'gif', 'webp']):
        return jsonify({'error': 'Invalid file type. Only images allowed'}), 400
    
    try:
        # Save to notifications subdirectory
        filepath = save_upload(file, subdirectory='notifications')
        
        return jsonify({
            'message': 'Image uploaded successfully',
            'image_url': filepath
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


@bp.route('', methods=['GET'])
@jwt_required()
def get_notifications():
    """Get user notifications (both personal and global)"""
    user_id = int(get_jwt_identity())
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    
    # Get personal notifications
    personal_notifs = Notification.query.filter_by(user_id=user_id)\
        .order_by(Notification.created_at.desc())\
        .all()
    
    # Get global notifications for this user
    global_notifs_query = db.session.query(GlobalNotification)\
        .join(UserNotificationStatus, GlobalNotification.id == UserNotificationStatus.notification_id)\
        .filter(UserNotificationStatus.user_id == user_id)\
        .order_by(GlobalNotification.created_at.desc())\
        .all()
    
    # Combine and sort by created_at
    all_notifications = []
    
    for notif in personal_notifs:
        notif_dict = notif.to_dict()
        notif_dict['type'] = 'PERSONAL'
        notif_dict['notification_type'] = 'personal'  # For client compatibility
        all_notifications.append(notif_dict)
    
    for notif in global_notifs_query:
        notif_dict = notif.to_dict(user_id)
        notif_dict['notification_type'] = 'global'  # For client compatibility
        all_notifications.append(notif_dict)
    
    # Sort by created_at descending
    all_notifications.sort(key=lambda x: x['created_at'], reverse=True)
    
    # Manual pagination
    start = (page - 1) * limit
    end = start + limit
    paginated = all_notifications[start:end]
    
    return jsonify({
        'notifications': paginated,
        'total': len(all_notifications),
        'page': page,
        'pages': (len(all_notifications) + limit - 1) // limit
    }), 200


@bp.route('/<int:notification_id>/read', methods=['PUT'])
@jwt_required()
def mark_as_read(notification_id):
    """Mark notification as read"""
    user_id = int(get_jwt_identity())
    
    # Check if it's a personal notification
    notification = Notification.query.get(notification_id)
    if notification and notification.user_id == user_id:
        notification.is_read = True
        db.session.commit()
        return jsonify(notification.to_dict()), 200
    
    # Check if it's a global notification
    status = UserNotificationStatus.query.filter_by(
        notification_id=notification_id,
        user_id=user_id
    ).first()
    
    if status:
        status.is_read = True
        status.read_at = datetime.utcnow()
        db.session.commit()
        
        global_notif = GlobalNotification.query.get(notification_id)
        return jsonify(global_notif.to_dict(user_id)), 200
    
    return jsonify({'error': 'Notification not found'}), 404


@bp.route('/read-all', methods=['PUT'])
@jwt_required()
def mark_all_as_read():
    """Mark all notifications as read"""
    user_id = int(get_jwt_identity())
    
    # Mark all personal notifications as read
    Notification.query.filter_by(user_id=user_id, is_read=False)\
        .update({Notification.is_read: True})
    
    # Mark all global notifications as read
    UserNotificationStatus.query.filter_by(user_id=user_id, is_read=False)\
        .update({
            UserNotificationStatus.is_read: True,
            UserNotificationStatus.read_at: datetime.utcnow()
        })
    
    db.session.commit()
    
    return jsonify({'message': 'All notifications marked as read'}), 200
