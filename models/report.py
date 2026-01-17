from app.extensions import db
from datetime import datetime
import enum

class ReportCategory(enum.Enum):
    ACADEMIC = "ACADEMIC"
    FACILITIES = "FACILITIES"
    TECHNICAL = "TECHNICAL"
    OTHER = "OTHER"

class ReportPriority(enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class ReportStatus(enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"

class Report(db.Model):
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey('radios.id'), nullable=True)
    category = db.Column(db.Enum(ReportCategory), default=ReportCategory.OTHER, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    issue_type = db.Column(db.String(50))  # Keep for backward compatibility
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    priority = db.Column(db.Enum(ReportPriority), default=ReportPriority.MEDIUM, nullable=False)
    status = db.Column(db.Enum(ReportStatus), default=ReportStatus.PENDING, nullable=False)
    admin_reply = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    student = db.relationship('User', backref='reports')
    radio = db.relationship('Radio', backref='reports')
    
    def to_dict(self):
        from app.models.user import User
        
        student = User.query.get(self.student_id)
        
        # Handle image URL
        image_url_value = None
        if self.image_url:
            if self.image_url.startswith('/'):
                image_url_value = self.image_url
            else:
                image_url_value = f'/uploads/{self.image_url}'
        
        # Handle student profile picture
        student_profile = None
        if student and student.profile_picture:
            if student.profile_picture.startswith('/'):
                student_profile = student.profile_picture
            else:
                student_profile = f'/uploads/{student.profile_picture}'
        
        return {
            'id': self.id,
            'student_id': self.student_id,
            'student_name': student.name if student else "Unknown",
            'student_email': student.email if student else None,
            'student_profile': student_profile,
            'session_id': self.session_id,
            'session_title': self.radio.title if self.radio else None,
            'category': self.category.value if self.category else 'OTHER',
            'title': self.title,
            'issue_type': self.issue_type,  # Deprecated but kept for compatibility
            'description': self.description,
            'image_url': image_url_value,
            'priority': self.priority.value if self.priority else 'MEDIUM',
            'status': self.status.value if self.status else 'PENDING',
            'admin_reply': self.admin_reply,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Report {self.title} - {self.status.value}>'
