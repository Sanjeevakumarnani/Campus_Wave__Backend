from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.category import Category
from app.middleware.auth import admin_required

bp = Blueprint('categories', __name__, url_prefix='/api/categories')


@bp.route('', methods=['GET'])
def get_categories():
    """Get all categories"""
    categories = Category.query.all()
    return jsonify([cat.to_dict() for cat in categories]), 200


@bp.route('/<int:category_id>', methods=['GET'])
def get_category(category_id):
    """Get single category"""
    category = Category.query.get(category_id)
    if not category:
        return jsonify({'error': 'Category not found'}), 404
    return jsonify(category.to_dict()), 200


@bp.route('', methods=['POST'])
@admin_required
def create_category():
    """Create new category (admin only)"""
    data = request.get_json()
    
    if not data.get('name'):
        return jsonify({'error': 'Name is required'}), 400
    
    # Check if category already exists
    existing = Category.query.filter_by(name=data['name']).first()
    if existing:
        return jsonify({'error': 'Category already exists'}), 409
    
    category = Category(
        name=data['name'],
        color=data.get('color', '#5E72E4'),
        icon=data.get('icon', 'radio')
    )
    
    db.session.add(category)
    db.session.commit()
    
    return jsonify(category.to_dict()), 201


@bp.route('/<int:category_id>', methods=['PUT'])
@admin_required
def update_category(category_id):
    """Update category (admin only)"""
    category = Category.query.get(category_id)
    if not category:
        return jsonify({'error': 'Category not found'}), 404
    
    data = request.get_json()
    
    if 'name' in data:
        category.name = data['name']
    if 'color' in data:
        category.color = data['color']
    if 'icon' in data:
        category.icon = data['icon']
    
    db.session.commit()
    
    return jsonify(category.to_dict()), 200


@bp.route('/<int:category_id>', methods=['DELETE'])
@admin_required
def delete_category(category_id):
    """Delete category (admin only)"""
    category = Category.query.get(category_id)
    if not category:
        return jsonify({'error': 'Category not found'}), 404
    
    db.session.delete(category)
    db.session.commit()
    
    return jsonify({'message': 'Category deleted'}), 200


@bp.route('/seed', methods=['POST'])
@admin_required
def seed_categories():
    """Seed default categories (admin only)"""
    default_categories = [
        {'name': 'Sports', 'color': '#10B981', 'icon': 'sports'},
        {'name': 'Cultural', 'color': '#F59E0B', 'icon': 'theater_comedy'},
        {'name': 'Academic', 'color': '#3B82F6', 'icon': 'school'},
        {'name': 'Technical', 'color': '#8B5CF6', 'icon': 'computer'},
        {'name': 'Social', 'color': '#EC4899', 'icon': 'groups'},
        {'name': 'Workshop', 'color': '#06B6D4', 'icon': 'handyman'},
        {'name': 'Seminar', 'color': '#6366F1', 'icon': 'podium'},
        {'name': 'Other', 'color': '#6B7280', 'icon': 'radio'}
    ]
    
    created = []
    for cat_data in default_categories:
        existing = Category.query.filter_by(name=cat_data['name']).first()
        if not existing:
            category = Category(**cat_data)
            db.session.add(category)
            created.append(cat_data['name'])
    
    db.session.commit()
    
    return jsonify({
        'message': f'Created {len(created)} categories',
        'created': created
    }), 201
