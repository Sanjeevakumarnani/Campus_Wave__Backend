from app.extensions import db
from datetime import datetime
import enum

class SuggestionStatus(enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class RadioSuggestion(db.Model):
    __tablename__ = 'radio_suggestions'
    
    id = db.Column(db.Integer, primary_key=True)
    radio_title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    suggested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.Enum(SuggestionStatus), nullable=False, default=SuggestionStatus.PENDING)
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    
    # Relationship to reviewer
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref='reviewed_suggestions')
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            'id': self.id,
            'radio_title': self.radio_title,
            'description': self.description,
            'category': self.category,
            'suggested_by': self.suggested_by,
            'status': self.status.value,
            'reviewed_by': self.reviewed_by,
            'created_at': self.created_at.isoformat(),
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None
        }
    
    def __repr__(self):
        return f'<RadioSuggestion {self.radio_title}>'
