from app.extensions import db
from datetime import datetime

class Marquee(db.Model):
    __tablename__ = 'marquees'
    
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    text_color = db.Column(db.String(7), default='#FFFFFF')  # Hex color
    bg_color = db.Column(db.String(7), default='#4F46E5')    # Hex color
    speed = db.Column(db.String(10), default='medium')       # slow, medium, fast
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'text': self.text,
            'text_color': self.text_color,
            'bg_color': self.bg_color,
            'speed': self.speed,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
