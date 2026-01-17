from app.extensions import db
from datetime import datetime

class UpdateComment(db.Model):
    __tablename__ = 'update_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    update_id = db.Column(db.Integer, db.ForeignKey('updates.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        from app.models.user import User
        user = User.query.get(self.user_id)
        
        return {
            'id': self.id,
            'update_id': self.update_id,
            'user_id': self.user_id,
            'user_name': user.name if user else None,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<UpdateComment {self.id}>'
