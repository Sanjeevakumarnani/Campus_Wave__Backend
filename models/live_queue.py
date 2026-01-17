from datetime import datetime
from app.extensions import db

class LiveQueue(db.Model):
    __tablename__ = 'live_queue'
    
    id = db.Column(db.Integer, primary_key=True)
    radio_id = db.Column(db.Integer, db.ForeignKey('radios.id'), nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship to Radio to get title, media_url, etc.
    radio = db.relationship('Radio', backref=db.backref('queue_items', lazy='dynamic'))
    
    def to_dict(self):
        return {
            'id': self.id,
            'radio_id': self.radio_id,
            'position': self.position,
            'title': self.radio.title if self.radio else None,
            'media_url': self.radio.media_url if self.radio else None,
            'duration': self.radio.duration if hasattr(self.radio, 'duration') else None,
            'created_at': self.created_at.isoformat()
        }
