from datetime import datetime
from app.extensions import db

class GlobalNotification(db.Model):
    __tablename__ = 'global_notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self, current_user_id=None):
        from app.models.user import User
        
        creator = User.query.get(self.created_by)
        
        # Handle image URL
        image_url_value = None
        if self.image_url:
            if self.image_url.startswith('/'):
                image_url_value = self.image_url
            else:
                image_url_value = f'/uploads/{self.image_url}'
        
        result = {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'image_url': image_url_value,
            'created_by': self.created_by,
            'creator_name': creator.name if creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'type': 'GLOBAL'
        }
        
        # If current_user_id is provided, get read status
        if current_user_id:
            status = UserNotificationStatus.query.filter_by(
                notification_id=self.id,
                user_id=current_user_id
            ).first()
            
            result['is_read'] = status.is_read if status else False
            result['read_at'] = status.read_at.isoformat() if status and status.read_at else None
        else:
            result['is_read'] = False
            result['read_at'] = None
        
        return result
    
    def __repr__(self):
        return f'<GlobalNotification {self.title}>'


class UserNotificationStatus(db.Model):
    __tablename__ = 'user_notification_status'
    
    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.Integer, db.ForeignKey('global_notifications.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<UserNotificationStatus user={self.user_id} notification={self.notification_id} read={self.is_read}>'
