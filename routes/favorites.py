from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.favorite import Favorite
from app.models.radio import Radio

bp = Blueprint('favorites', __name__, url_prefix='/api')


@bp.route('/favorites', methods=['GET'])
@jwt_required()
def get_favorites():
    """Get user's favorite radio sessions"""
    user_id = int(get_jwt_identity())
    
    favorites = Favorite.query.filter_by(user_id=user_id).all()
    radios = [Radio.query.get(fav.radio_id) for fav in favorites]
    radios = [r for r in radios if r is not None]  # Filter out deleted radios
    
    return jsonify([radio.to_dict(user_id=user_id) for radio in radios]), 200


@bp.route('/radios/<int:radio_id>/favorite', methods=['POST'])
@jwt_required()
def add_favorite(radio_id):
    """Add radio session to favorites"""
    user_id = int(get_jwt_identity())
    
    radio = Radio.query.get(radio_id)
    if not radio:
        return jsonify({'error': 'Radio session not found'}), 404
    
    # Check if already favorited
    existing = Favorite.query.filter_by(user_id=user_id, radio_id=radio_id).first()
    if existing:
        return jsonify({'message': 'Already in favorites'}), 200
    
    favorite = Favorite(user_id=user_id, radio_id=radio_id)
    db.session.add(favorite)
    db.session.commit()
    
    return jsonify({
        'message': 'Added to favorites',
        'radio': radio.to_dict(user_id=user_id)
    }), 201


@bp.route('/radios/<int:radio_id>/favorite', methods=['DELETE'])
@jwt_required()
def remove_favorite(radio_id):
    """Remove radio session from favorites"""
    user_id = int(get_jwt_identity())
    
    favorite = Favorite.query.filter_by(user_id=user_id, radio_id=radio_id).first()
    if not favorite:
        return jsonify({'error': 'Not in favorites'}), 404
    
    db.session.delete(favorite)
    db.session.commit()
    
    return jsonify({'message': 'Removed from favorites'}), 200


@bp.route('/radios/<int:radio_id>/favorite/toggle', methods=['POST'])
@jwt_required()
def toggle_favorite(radio_id):
    """Toggle favorite status for a radio session"""
    user_id = int(get_jwt_identity())
    
    radio = Radio.query.get(radio_id)
    if not radio:
        return jsonify({'error': 'Radio session not found'}), 404
    
    existing = Favorite.query.filter_by(user_id=user_id, radio_id=radio_id).first()
    
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({
            'message': 'Removed from favorites',
            'is_favorited': False
        }), 200
    else:
        favorite = Favorite(user_id=user_id, radio_id=radio_id)
        db.session.add(favorite)
        db.session.commit()
        return jsonify({
            'message': 'Added to favorites',
            'is_favorited': True
        }), 201
