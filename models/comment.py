from app.extensions import db
from datetime import datetime


class Comment(db.Model):
    """Radio comments/chat model"""
    __tablename__ = 'comments'
    
    id = db.Column(db.Integer, primary_key=True)
    radio_id = db.Column(db.Integer, db.ForeignKey('radios.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('comments', lazy='dynamic'))
    radio = db.relationship('Radio', backref=db.backref('comments', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'radio_id': self.radio_id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else 'Unknown',
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
