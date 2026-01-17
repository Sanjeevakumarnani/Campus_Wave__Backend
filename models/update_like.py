from app.extensions import db
from datetime import datetime

class UpdateLike(db.Model):
    __tablename__ = 'update_likes'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    update_id = db.Column(db.Integer, db.ForeignKey('updates.id'), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('liked_updates', lazy='dynamic'))
    update = db.relationship('Update', backref=db.backref('likes', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'user_id': self.user_id,
            'update_id': self.update_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
