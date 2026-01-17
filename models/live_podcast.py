from datetime import datetime
from app.extensions import db
import enum

class PodcastStatus(enum.Enum):
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    ENDED = "ENDED"

class LivePodcast(db.Model):
    __tablename__ = 'live_podcasts'
    
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.Enum(PodcastStatus), default=PodcastStatus.SCHEDULED, nullable=False)
    scheduled_start_time = db.Column(db.DateTime)
    actual_start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    stream_url = db.Column(db.String(500))
    listener_peak_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        from app.models.user import User
        
        admin = User.query.get(self.admin_id)
        
        return {
            'id': self.id,
            'admin_id': self.admin_id,
            'admin_name': admin.name if admin else None,
            'title': self.title,
            'description': self.description,
            'status': self.status.value if self.status else 'SCHEDULED',
            'scheduled_start_time': self.scheduled_start_time.isoformat() if self.scheduled_start_time else None,
            'actual_start_time': self.actual_start_time.isoformat() if self.actual_start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'stream_url': self.stream_url,
            'listener_peak_count': self.listener_peak_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<LivePodcast {self.title} - {self.status.value}>'
