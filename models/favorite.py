from app.extensions import db
from datetime import datetime


class Favorite(db.Model):
    """User's favorite radios"""
    __tablename__ = 'favorites'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    radio_id = db.Column(db.Integer, db.ForeignKey('radios.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('favorites', lazy='dynamic'))
    radio = db.relationship('Radio', backref=db.backref('favorited_by', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'radio_id': self.radio_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
