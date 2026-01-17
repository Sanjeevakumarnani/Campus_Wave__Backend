from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.update import Update, UpdateCategory, MediaType
from app.models.update_comment import UpdateComment
from app.models.update_like import UpdateLike
from app.models.update_reaction import UpdateReaction, ALLOWED_EMOJIS
from app.models.notification import Notification
from app.models.user import User, UserRole
from app.middleware.auth import admin_required
from app.utils.upload import save_upload, allowed_file

bp = Blueprint('updates', __name__, url_prefix='/api/updates')

@bp.route('', methods=['GET'])
@jwt_required(optional=True)
def get_updates():
    """Get all updates (paginated)"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    category = request.args.get('category', type=str)
    
    query = Update.query
    
    # Filter by category if specified
    if category:
        try:
            category_enum = UpdateCategory[category.upper()]
            query = query.filter_by(category=category_enum)
        except KeyError:
            pass
    
    # Sort by pinned status and then newest first
    query = query.order_by(Update.is_pinned.desc(), Update.created_at.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    
    # Get current user for like status
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id) if current_user_id else None
    
    return jsonify({
        'updates': [update.to_dict(current_user_id=user_id) for update in pagination.items],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    }), 200

@bp.route('/<int:update_id>', methods=['GET'])
def get_update(update_id):
    """Get single update details"""
    update = Update.query.get(update_id)
    if not update:
        return jsonify({'error': 'Update not found'}), 404
    
    # Get current user for like status
    current_user_id = get_jwt_identity()
    user_id = int(current_user_id) if current_user_id else None
    
    return jsonify(update.to_dict(current_user_id=user_id)), 200

@bp.route('', methods=['POST'])
@admin_required
def create_update():
    """Create new update (admin only)"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # Validate required fields
    if not data.get('title'):
        return jsonify({'error': 'Title is required'}), 400
    if not data.get('category'):
        return jsonify({'error': 'Category is required'}), 400
    
    try:
        category = UpdateCategory[data['category'].upper()]
    except KeyError:
        return jsonify({'error': 'Invalid category. Use COLLEGE, CLUB, or MOTIVATION'}), 400
    
    # Create update
    update = Update(
        title=data['title'],
        description=data.get('description', ''),
        category=category,
        is_pinned=data.get('is_pinned', False),
        media_type=MediaType.NONE,
        created_by=user_id
    )
    
    db.session.add(update)
    db.session.commit()
    
    # Send notifications to all students if requested
    if data.get('send_notification', True):
        students = User.query.filter_by(role=UserRole.STUDENT).all()
        for student in students:
            notification = Notification(
                user_id=student.id,
                title="New Campus Update! 📢",
                message=f"New {category.value.lower()} update: {data['title']}",
                type="UPDATE",
                related_id=update.id
            )
            db.session.add(notification)
        db.session.commit()
    
    return jsonify(update.to_dict()), 201

@bp.route('/<int:update_id>', methods=['PUT'])
@admin_required
def update_update(update_id):
    """Update an existing update (admin only)"""
    update = Update.query.get(update_id)
    if not update:
        return jsonify({'error': 'Update not found'}), 404
    
    data = request.get_json()
    
    # Update fields
    if 'title' in data:
        update.title = data['title']
    if 'description' in data:
        update.description = data['description']
    if 'category' in data:
        try:
            update.category = UpdateCategory[data['category'].upper()]
        except KeyError:
            return jsonify({'error': 'Invalid category'}), 400
    
    db.session.commit()
    
    return jsonify(update.to_dict()), 200

@bp.route('/<int:update_id>', methods=['DELETE'])
@admin_required
def delete_update(update_id):
    """Delete an update (admin only)"""
    update = Update.query.get(update_id)
    if not update:
        return jsonify({'error': 'Update not found'}), 404
    
    # Import related models
    from app.models.update_like import UpdateLike
    from app.models.update_comment import UpdateComment
    
    # Delete all related likes first
    UpdateLike.query.filter_by(update_id=update_id).delete()
    
    # Delete all related comments
    UpdateComment.query.filter_by(update_id=update_id).delete()
    
    # Now delete the update itself
    db.session.delete(update)
    db.session.commit()
    
    return jsonify({'message': 'Update deleted successfully'}), 200

@bp.route('/<int:update_id>/upload-media', methods=['POST'])
@admin_required
def upload_media(update_id):
    """Upload media (image/video) for update (admin only)"""
    update = Update.query.get(update_id)
    if not update:
        return jsonify({'error': 'Update not found'}), 404
    
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
    
    # Determine media type based on file extension
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
        update.media_type = MediaType.IMAGE
    elif ext in ['mp4', 'mov', 'avi', 'webm', 'mkv']:
        update.media_type = MediaType.VIDEO
    else:
        update.media_type = MediaType.NONE
    
    update.media_url = filename
    db.session.commit()
    
    return jsonify({
        'message': 'Media uploaded successfully',
        'media_url': f'/uploads/{filename}',
        'media_type': update.media_type.value
    }), 200

# EMOJI REACTIONS ENDPOINTS (Replacing Comments)

@bp.route('/<int:update_id>/react', methods=['POST'])
@jwt_required()
def add_or_change_reaction(update_id):
    """Add or change emoji reaction to an update"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    emoji = data.get('emoji', '').strip()
    
    if not emoji:
        return jsonify({'error': 'Emoji is required'}), 400
    
    if not UpdateReaction.validate_emoji(emoji):
        return jsonify({
            'error': 'Invalid emoji. Allowed emojis: 👍 ❤️ 😂 😮 😢 🔥'
        }), 400
    
    update = Update.query.get(update_id)
    if not update:
        return jsonify({'error': 'Update not found'}), 404
    
    # Check if user already has a reaction
    existing_reaction = UpdateReaction.query.filter_by(
        update_id=update_id,
        user_id=user_id
    ).first()
    
    if existing_reaction:
        # Change existing reaction
        existing_reaction.emoji = emoji
        message = 'Reaction changed successfully'
    else:
        # Add new reaction
        new_reaction = UpdateReaction(
            update_id=update_id,
            user_id=user_id,
            emoji=emoji
        )
        db.session.add(new_reaction)
        message = 'Reaction added successfully'
    
    db.session.commit()
    
    # Get updated reaction counts
    reaction_counts = UpdateReaction.get_reaction_counts(update_id)
    
    return jsonify({
        'message': message,
        'user_reaction': emoji,
        'reactions': reaction_counts
    }), 200


@bp.route('/<int:update_id>/react', methods=['DELETE'])
@jwt_required()
def remove_reaction(update_id):
    """Remove user's reaction from an update"""
    user_id = int(get_jwt_identity())
    
    reaction = UpdateReaction.query.filter_by(
        update_id=update_id,
        user_id=user_id
    ).first()
    
    if not reaction:
        return jsonify({'error': 'No reaction found to remove'}), 404
    
    db.session.delete(reaction)
    db.session.commit()
    
    # Get updated reaction counts
    reaction_counts = UpdateReaction.get_reaction_counts(update_id)
    
    return jsonify({
        'message': 'Reaction removed successfully',
        'reactions': reaction_counts
    }), 200


@bp.route('/<int:update_id>/reactions', methods=['GET'])
@jwt_required(optional=True)
def get_reactions(update_id):
    """Get reaction counts and user's reaction for an update"""
    update = Update.query.get(update_id)
    if not update:
        return jsonify({'error': 'Update not found'}), 404
    
    # Get reaction counts
    reaction_counts = UpdateReaction.get_reaction_counts(update_id)
    
    # Get current user's reaction if logged in
    user_reaction = None
    current_user_id = get_jwt_identity()
    if current_user_id:
        user_reaction_obj = UpdateReaction.query.filter_by(
            update_id=update_id,
            user_id=int(current_user_id)
        ).first()
        if user_reaction_obj:
            user_reaction = user_reaction_obj.emoji
    
    return jsonify({
        'reactions': reaction_counts,
        'user_reaction': user_reaction
    }), 200

@bp.route('/<int:update_id>/like', methods=['POST'])
@jwt_required()
def toggle_like(update_id):
    """Toggle like/unlike for an update"""
    user_id = int(get_jwt_identity())
    update = Update.query.get(update_id)
    if not update:
        return jsonify({'error': 'Update not found'}), 404
    
    like = UpdateLike.query.filter_by(user_id=user_id, update_id=update_id).first()
    
    if like:
        db.session.delete(like)
        liked = False
    else:
        like = UpdateLike(user_id=user_id, update_id=update_id)
        db.session.add(like)
        liked = True
    
    db.session.commit()
    
    # Get updated like count
    like_count = UpdateLike.query.filter_by(update_id=update_id).count()
    
    return jsonify({
        'liked': liked,
        'likes_count': like_count
    }), 200

@bp.route('/<int:update_id>/likes', methods=['GET'])
@jwt_required(optional=True)
def get_likes(update_id):
    """Get like status and count for an update"""
    current_user_id = get_jwt_identity()
    update = Update.query.get(update_id)
    if not update:
        return jsonify({'error': 'Update not found'}), 404
    
    is_liked = False
    if current_user_id:
        like = UpdateLike.query.filter_by(user_id=int(current_user_id), update_id=update_id).first()
        is_liked = like is not None
        
    like_count = UpdateLike.query.filter_by(update_id=update_id).count()
    
    return jsonify({
        'liked': is_liked,
        'likes_count': like_count
    }), 200
