from datetime import datetime
from app.extensions import db

class LiveStream(db.Model):
    __tablename__ = 'live_streams'
    
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), default='OFFLINE')  # ONLINE, OFFLINE
    title = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime, nullable=True)
    current_audio_id = db.Column(db.Integer, nullable=True)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        # Import here to avoid circular dependency
        from app.models.radio_listener import RadioListener
        from app.models.radio import Radio
        
        data = {
            'id': self.id,
            'status': self.status,
            'title': self.title,
            'description': self.description,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'current_audio_id': self.current_audio_id,
            'updated_at': self.updated_at.isoformat(),
            'listener_count': RadioListener.get_active_count() if self.status == 'ONLINE' else 0
        }

        # Include details of the currently playing audio
        if self.current_audio_id:
            radio = Radio.query.get(self.current_audio_id)
            if radio:
                data['media_url'] = radio.media_url
                data['banner_image'] = radio.banner_image
                # Optional: Override title/desc if they are generic, but let's keep stream title for now
                # or provide them as separate fields
                data['current_track_title'] = radio.title
                data['current_track_artist'] = radio.created_by # Or convert to name if possible
        
        return data

