from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.review import Review
from app.models.radio import Radio

bp = Blueprint('reviews', __name__, url_prefix='/api/reviews')

@bp.route('/<int:radio_id>', methods=['POST'])
@jwt_required()
def create_review(radio_id):
    """Submit a review for a radio session"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    radio = Radio.query.get(radio_id)
    if not radio:
        return jsonify({'error': 'Radio session not found'}), 404
        
    if not data or 'rating' not in data:
        return jsonify({'error': 'Rating is required'}), 400
        
    rating = data['rating']
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({'error': 'Rating must be between 1 and 5'}), 400

    # Check if already reviewed
    existing = Review.query.filter_by(radio_id=radio_id, user_id=user_id).first()
    if existing:
        # Update existing? Or block? Let's block for now as per simple req
        return jsonify({'error': 'You have already reviewed this session'}), 409

    review = Review(
        radio_id=radio_id,
        user_id=user_id,
        rating=rating,
        comment=data.get('comment', '')
    )
    
    db.session.add(review)
    db.session.commit()
    
    return jsonify(review.to_dict()), 201

@bp.route('/<int:radio_id>', methods=['GET'])
def get_radio_reviews(radio_id):
    """Get all reviews for a radio session"""
    reviews = Review.query.filter_by(radio_id=radio_id).order_by(Review.created_at.desc()).all()
    return jsonify([r.to_dict() for r in reviews]), 200
