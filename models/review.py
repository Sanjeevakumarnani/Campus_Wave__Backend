from app.extensions import db
from datetime import datetime

class Review(db.Model):
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    radio_id = db.Column(db.Integer, db.ForeignKey('radios.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False) # 1-5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='reviews')
    radio = db.relationship('Radio', backref='reviews')
    
    def to_dict(self):
        return {
            'id': self.id,
            'radio_id': self.radio_id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else 'Unknown',
            'rating': self.rating,
            'comment': self.comment,
            'created_at': self.created_at.isoformat()
        }
