from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime, timedelta
from sqlalchemy import func
from app.extensions import db
from app.models.radio import Radio, RadioStatus
from app.models.user import User, UserRole
from app.models.comment import Comment
from app.models.favorite import Favorite
from app.models.category import Category
from app.middleware.auth import admin_required

bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')


@bp.route('/overview', methods=['GET'])
@admin_required
def get_overview():
    """Get overview analytics for admin dashboard"""
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # Total counts
    total_radios = Radio.query.count()
    total_users = User.query.count()
    total_students = User.query.filter_by(role=UserRole.STUDENT).count()
    total_admins = User.query.filter_by(role=UserRole.ADMIN).count()
    total_comments = Comment.query.count()
    total_favorites = Favorite.query.count()
    
    # Radio stats
    live_radios = Radio.query.filter_by(status=RadioStatus.LIVE).count()
    upcoming_radios = Radio.query.filter_by(status=RadioStatus.UPCOMING).count()
    completed_radios = Radio.query.filter_by(status=RadioStatus.COMPLETED).count()
    
    # Recent activity
    radios_this_week = Radio.query.filter(Radio.created_at >= week_ago).count()
    radios_this_month = Radio.query.filter(Radio.created_at >= month_ago).count()
    # NOTE: User model doesn't have created_at field, so we can't track new users by week
    comments_this_week = Comment.query.filter(Comment.created_at >= week_ago).count()
    
    return jsonify({
        'totals': {
            'radios': total_radios,
            'users': total_users,
            'students': total_students,
            'admins': total_admins,
            'comments': total_comments,
            'favorites': total_favorites
        },
        'radios': {
            'live': live_radios,
            'upcoming': upcoming_radios,
            'completed': completed_radios
        },
        'recent': {
            'radios_this_week': radios_this_week,
            'radios_this_month': radios_this_month,
            'comments_this_week': comments_this_week
        }
    }), 200


@bp.route('/radios', methods=['GET'])
@admin_required
def get_radio_analytics():
    """Get detailed radio analytics"""
    # Top radios by favorites
    top_favorited = db.session.query(
        Radio.id, Radio.title, func.count(Favorite.radio_id).label('favorite_count')
    ).outerjoin(Favorite).group_by(Radio.id).order_by(
        func.count(Favorite.radio_id).desc()
    ).limit(10).all()
    
    # Top radios by comments
    top_commented = db.session.query(
        Radio.id, Radio.title, func.count(Comment.radio_id).label('comment_count')
    ).outerjoin(Comment).group_by(Radio.id).order_by(
        func.count(Comment.radio_id).desc()
    ).limit(10).all()
    
    # Radios by category
    radios_by_category = db.session.query(
        Category.name, func.count(Radio.id).label('count')
    ).outerjoin(Radio).group_by(Category.id).all()
    
    # Radios by status
    radios_by_status = db.session.query(
        Radio.status, func.count(Radio.id).label('count')
    ).group_by(Radio.status).all()
    
    return jsonify({
        'top_favorited': [
            {'id': r.id, 'title': r.title, 'favorites': r.favorite_count}
            for r in top_favorited
        ],
        'top_commented': [
            {'id': r.id, 'title': r.title, 'comments': r.comment_count}
            for r in top_commented
        ],
        'by_category': [
            {'category': c.name or 'Uncategorized', 'count': c.count}
            for c in radios_by_category
        ],
        'by_status': [
            {'status': s.status.value if s.status else 'Unknown', 'count': s.count}
            for s in radios_by_status
        ]
    }), 200


@bp.route('/trends', methods=['GET'])
@admin_required
def get_trends():
    """Get weekly/monthly trends"""
    now = datetime.now()
    
    # Radios created per day (last 7 days)
    daily_radios = []
    for i in range(7):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = Radio.query.filter(
            Radio.created_at >= day_start,
            Radio.created_at < day_end
        ).count()
        daily_radios.append({
            'date': day_start.strftime('%Y-%m-%d'),
            'count': count
        })
    
    # User signups per day (last 7 days)
    daily_users = []
    for i in range(7):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = User.query.filter(
            User.created_at >= day_start,
            User.created_at < day_end
        ).count()
        daily_users.append({
            'date': day_start.strftime('%Y-%m-%d'),
            'count': count
        })
    
    return jsonify({
        'daily_radios': list(reversed(daily_radios)),
        'daily_users': list(reversed(daily_users))
    }), 200
