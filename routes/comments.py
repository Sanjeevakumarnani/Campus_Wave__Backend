from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app.extensions import db
from app.models.comment import Comment
from app.models.radio import Radio
from app.middleware.auth import admin_required

bp = Blueprint('comments', __name__, url_prefix='/api')


@bp.route('/radios/<int:radio_id>/comments', methods=['GET'])
def get_comments(radio_id):
    """Get all comments for a radio session"""
    radio = Radio.query.get(radio_id)
    if not radio:
        return jsonify({'error': 'Radio session not found'}), 404
    
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 50, type=int)
    
    comments = Comment.query.filter_by(radio_id=radio_id)\
        .order_by(Comment.created_at.desc())\
        .paginate(page=page, per_page=limit, error_out=False)
    
    return jsonify({
        'comments': [c.to_dict() for c in comments.items],
        'total': comments.total,
        'page': page,
        'pages': comments.pages
    }), 200


@bp.route('/radios/<int:radio_id>/comments', methods=['POST'])
@jwt_required()
def add_comment(radio_id):
    """Add a comment to a radio session"""
    user_id = int(get_jwt_identity())
    
    radio = Radio.query.get(radio_id)
    if not radio:
        return jsonify({'error': 'Radio session not found'}), 404
    
    data = request.get_json()
    content = data.get('content', '').strip()
    
    if not content:
        return jsonify({'error': 'Content is required'}), 400
    
    if len(content) > 1000:
        return jsonify({'error': 'Comment too long (max 1000 characters)'}), 400
    
    comment = Comment(
        radio_id=radio_id,
        user_id=user_id,
        content=content
    )
    
    db.session.add(comment)
    db.session.commit()
    
    return jsonify(comment.to_dict()), 201


@bp.route('/comments/<int:comment_id>', methods=['DELETE'])
@jwt_required()
def delete_comment(comment_id):
    """Delete a comment (owner or admin only)"""
    user_id = int(get_jwt_identity())
    
    comment = Comment.query.get(comment_id)
    if not comment:
        return jsonify({'error': 'Comment not found'}), 404
    
    # Check if user is owner or admin
    from app.models.user import User, UserRole
    user = User.query.get(user_id)
    
    if comment.user_id != user_id and user.role != UserRole.ADMIN:
        return jsonify({'error': 'Unauthorized'}), 403
    
    db.session.delete(comment)
    db.session.commit()
    
    return jsonify({'message': 'Comment deleted'}), 200


@bp.route('/radios/<int:radio_id>/comments/recent', methods=['GET'])
def get_recent_comments(radio_id):
    """Get recent comments for live chat display"""
    radio = Radio.query.get(radio_id)
    if not radio:
        return jsonify({'error': 'Radio session not found'}), 404
    
    # Get last N comments for live updates
    limit = request.args.get('limit', 20, type=int)
    since = request.args.get('since')  # ISO datetime string
    
    query = Comment.query.filter_by(radio_id=radio_id)
    
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            query = query.filter(Comment.created_at > since_dt)
        except:
            pass
    
    comments = query.order_by(Comment.created_at.asc()).limit(limit).all()
    
    return jsonify([c.to_dict() for c in comments]), 200
