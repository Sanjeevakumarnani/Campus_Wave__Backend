from app.extensions import db
from datetime import datetime
import enum

class RadioStatus(enum.Enum):
    DRAFT = "DRAFT"
    LIVE = "LIVE"
    UPCOMING = "UPCOMING"
    COMPLETED = "COMPLETED"

class MediaType(enum.Enum):
    NONE = "NONE"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"

class HostStatus(enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    HOSTING = "HOSTING"
    PAUSED = "PAUSED"
    ENDED = "ENDED"

# Association table for many-to-many relationship
radio_participants = db.Table('radio_participants',
    db.Column('radio_id', db.Integer, db.ForeignKey('radios.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('joined_at', db.DateTime, default=datetime.now)
)

class Radio(db.Model):
    __tablename__ = 'radios'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    banner_image = db.Column(db.String(255))
    media_url = db.Column(db.String(255))  # For MP3/MP4 files
    recording_url = db.Column(db.String(255))  # For saved recordings
    location = db.Column(db.String(200))
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.Enum(RadioStatus), nullable=False, default=RadioStatus.UPCOMING)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Category relationship
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    category = db.relationship('Category', back_populates='radios')
    
    # Live hosting fields
    media_type = db.Column(db.Enum(MediaType), nullable=False, default=MediaType.NONE)
    host_status = db.Column(db.Enum(HostStatus), nullable=False, default=HostStatus.NOT_STARTED)
    hosted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    stream_started_at = db.Column(db.DateTime, nullable=True)
    
    # Audio/Video duration in seconds
    duration = db.Column(db.Integer, nullable=True, default=0)
    
    # Relationships
    participants = db.relationship('User', secondary=radio_participants, backref='participated_radios', lazy='dynamic')
    
    @property
    def participant_count(self):
        """Get count of participants"""
        return self.participants.count()
    
    @property
    def favorite_count(self):
        """Get count of users who favorited this radio"""
        return self.favorited_by.count() if hasattr(self, 'favorited_by') else 0
    
    def to_dict(self, user_id=None):
        """Convert to dictionary for JSON response"""
        # Handle media_url - check for empty string as well as None
        media_url_value = None
        if self.media_url and len(self.media_url.strip()) > 0:
            if self.media_url.startswith('/'):
                media_url_value = self.media_url
            else:
                media_url_value = f'/uploads/{self.media_url}'
        
        # Handle banner_image - check for empty string as well as None
        banner_image_value = None
        if self.banner_image and len(self.banner_image.strip()) > 0:
            if self.banner_image.startswith('/'):
                banner_image_value = self.banner_image
            else:
                banner_image_value = f'/uploads/{self.banner_image}'
        
        result = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'banner_image': banner_image_value,
            'media_url': media_url_value,
            'recording_url': self.recording_url,
            'location': self.location,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status.value,
            'created_by': self.created_by,
            'participant_count': self.participant_count,
            'favorite_count': self.favorite_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'media_type': self.media_type.value if self.media_type else 'NONE',
            'host_status': self.host_status.value if self.host_status else 'NOT_STARTED',
            'hosted_by': self.hosted_by,
            'stream_started_at': self.stream_started_at.isoformat() if self.stream_started_at else None,
            'category_id': self.category_id,
            'category': self.category.to_dict() if self.category else None,
            'duration': self.duration or 0
        }
        
        # Check if user has favorited this radio
        if user_id:
            from app.models.favorite import Favorite
            result['is_favorited'] = Favorite.query.filter_by(
                user_id=user_id, radio_id=self.id
            ).first() is not None
        
        return result
    
    def __repr__(self):
        return f'<Radio {self.title}>'
