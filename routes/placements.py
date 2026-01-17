from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.placement import Placement
from app.models.user import User, UserRole
from app.middleware.auth import admin_required
from app.utils.upload import save_upload, allowed_file, delete_file
from datetime import datetime
import os

bp = Blueprint('placements', __name__, url_prefix='/api/placements')

# Allowed image extensions
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_image(filename):
    """Check if file is an allowed image type"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

@bp.route('', methods=['GET'])
@jwt_required(optional=True)
def get_placements():
    """Get all placements (paginated)"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    
    query = Placement.query.order_by(Placement.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    
    return jsonify({
        'placements': [placement.to_dict() for placement in pagination.items],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    }), 200

@bp.route('/<int:placement_id>', methods=['GET'])
def get_placement(placement_id):
    """Get single placement details"""
    placement = Placement.query.get(placement_id)
    if not placement:
        return jsonify({'error': 'Placement not found'}), 404
    
    return jsonify(placement.to_dict()), 200

@bp.route('', methods=['POST'])
@admin_required
def create_placement():
    """Create new placement (admin only)"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # Validate required fields
    if not data.get('company_name'):
        return jsonify({'error': 'Company name is required'}), 400
    if not data.get('position'):
        return jsonify({'error': 'Position is required'}), 400
    
    deadline = None
    if data.get('deadline'):
        try:
            deadline = datetime.fromisoformat(data['deadline'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid deadline format. Use ISO format.'}), 400
    
    placement = Placement(
        company_name=data['company_name'],
        position=data['position'],
        description=data.get('description', ''),
        application_link=data.get('application_link', ''),
        deadline=deadline,
        created_by=user_id
    )
    
    db.session.add(placement)
    db.session.commit()
    
    return jsonify(placement.to_dict()), 201

@bp.route('/<int:placement_id>', methods=['PUT'])
@admin_required
def update_placement(placement_id):
    """Update an existing placement (admin only)"""
    placement = Placement.query.get(placement_id)
    if not placement:
        return jsonify({'error': 'Placement not found'}), 404
    
    data = request.get_json()
    
    if 'company_name' in data:
        placement.company_name = data['company_name']
    if 'position' in data:
        placement.position = data['position']
    if 'description' in data:
        placement.description = data['description']
    if 'application_link' in data:
        placement.application_link = data['application_link']
    if 'deadline' in data and data['deadline']:
        try:
            placement.deadline = datetime.fromisoformat(data['deadline'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid deadline format'}), 400
            
    db.session.commit()
    
    return jsonify(placement.to_dict()), 200

@bp.route('/<int:placement_id>', methods=['DELETE'])
@admin_required
def delete_placement(placement_id):
    """Delete a placement (admin only)"""
    placement = Placement.query.get(placement_id)
    if not placement:
        return jsonify({'error': 'Placement not found'}), 404
    
    # Delete associated image file if exists
    if placement.image_url:
        filename = placement.image_url.split('/')[-1]
        delete_file(filename)
    
    db.session.delete(placement)
    db.session.commit()
    
    return jsonify({'message': 'Placement deleted successfully'}), 200


# ==================== Image Upload Endpoints ====================

@bp.route('/<int:placement_id>/upload-image', methods=['POST'])
@admin_required
def upload_placement_image(placement_id):
    """Upload image for a placement (admin only)"""
    placement = Placement.query.get(placement_id)
    if not placement:
        return jsonify({'error': 'Placement not found'}), 404
    
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image selected'}), 400
    
    # Validate file extension
    if not allowed_image(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: JPG, PNG, WEBP'}), 400
    
    # Check file size
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    
    if size > MAX_IMAGE_SIZE:
        return jsonify({'error': 'File too large. Maximum size is 5MB'}), 400
    
    # Delete old image if exists
    if placement.image_url:
        old_filename = placement.image_url.split('/')[-1]
        delete_file(old_filename)
    
    # Save new image with compression
    try:
        filename = save_upload(file, compress_image=True)
        if not filename:
            return jsonify({'error': 'Failed to save image'}), 500
        
        placement.image_url = f"/uploads/{filename}"
        db.session.commit()
        
        return jsonify({
            'message': 'Image uploaded successfully',
            'placement': placement.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


@bp.route('/<int:placement_id>/image', methods=['DELETE'])
@admin_required
def delete_placement_image(placement_id):
    """Delete image from a placement (admin only)"""
    placement = Placement.query.get(placement_id)
    if not placement:
        return jsonify({'error': 'Placement not found'}), 404
    
    if not placement.image_url:
        return jsonify({'error': 'No image to delete'}), 400
    
    # Delete file
    filename = placement.image_url.split('/')[-1]
    delete_file(filename)
    
    # Update database
    placement.image_url = None
    db.session.commit()
    
    return jsonify({
        'message': 'Image deleted successfully',
        'placement': placement.to_dict()
    }), 200

