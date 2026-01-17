from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.banner import Banner
from app.middleware.auth import admin_required
from app.utils.upload import save_upload, allowed_file, delete_file

bp = Blueprint('banners', __name__, url_prefix='/api/banners')

@bp.route('', methods=['GET'])
def get_banners():
    """Get all active banners ordered by sequence"""
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    
    query = Banner.query
    if active_only:
        query = query.filter_by(is_active=True)
        
    banners = query.order_by(Banner.order.asc(), Banner.created_at.desc()).all()
    
    return jsonify([banner.to_dict() for banner in banners]), 200

@bp.route('', methods=['POST'])
@admin_required
def create_banner():
    """Create new banner with image upload (admin only)"""
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400
    
    # Save image
    filename = save_upload(file)
    if not filename:
        return jsonify({'error': 'Failed to save image. File type might not be allowed.'}), 400
    
    link_url = request.form.get('link_url')
    order = request.form.get('order', 0, type=int)
    
    banner = Banner(
        image_url=f"/uploads/{filename}",
        link_url=link_url,
        order=order
    )
    
    db.session.add(banner)
    db.session.commit()
    
    return jsonify(banner.to_dict()), 201

@bp.route('/<int:banner_id>', methods=['PUT'])
@admin_required
def update_banner(banner_id):
    """Update banner details (admin only)"""
    banner = Banner.query.get(banner_id)
    if not banner:
        return jsonify({'error': 'Banner not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    if 'link_url' in data:
        banner.link_url = data['link_url']
    if 'order' in data:
        banner.order = data['order']
    if 'is_active' in data:
        banner.is_active = data['is_active']
        
    db.session.commit()
    
    return jsonify(banner.to_dict()), 200

@bp.route('/<int:banner_id>', methods=['DELETE'])
@admin_required
def delete_banner(banner_id):
    """Delete banner and its image file (admin only)"""
    banner = Banner.query.get(banner_id)
    if not banner:
        return jsonify({'error': 'Banner not found'}), 404
    
    # Delete image file
    if banner.image_url:
        filename = banner.image_url.split('/')[-1]
        delete_file(filename)
        
    db.session.delete(banner)
    db.session.commit()
    
    return jsonify({'message': 'Banner deleted successfully'}), 200
