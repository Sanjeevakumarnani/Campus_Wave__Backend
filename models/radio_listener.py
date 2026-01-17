from datetime import datetime
from app.extensions import db

class RadioListener(db.Model):
    """Track active listeners for the 24/7 live radio stream"""
    __tablename__ = 'radio_listeners'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), unique=True, nullable=False)  # Unique session identifier
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # NULL for anonymous
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_heartbeat = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 compatible
    device_info = db.Column(db.String(255), nullable=True)
    
    # Relationship to User
    user = db.relationship('User', backref=db.backref('listening_sessions', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else 'Anonymous',
            'joined_at': self.joined_at.isoformat() if self.joined_at else None,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None
        }
    
    @classmethod
    def get_active_count(cls, timeout_minutes=5):
        """Get count of listeners active within the timeout period"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        return cls.query.filter(cls.last_heartbeat >= cutoff).count()
    
    @classmethod
    def cleanup_stale(cls, timeout_minutes=5):
        """Remove listeners who haven't sent a heartbeat recently"""
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(minutes=timeout_minutes)
        stale = cls.query.filter(cls.last_heartbeat < cutoff).all()
        for listener in stale:
            db.session.delete(listener)
        db.session.commit()
        return len(stale)
