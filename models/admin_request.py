from app.extensions import db
from datetime import datetime
import enum

class RequestStatus(enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class AdminRequest(db.Model):
    __tablename__ = 'admin_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Enum(RequestStatus), nullable=False, default=RequestStatus.PENDING)
    department = db.Column(db.String(100), nullable=True)
    reason_for_access = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': 'ADMIN',
            'status': self.status.value,
            'department': self.department,
            'reason_for_access': self.reason_for_access,
            'created_at': self.created_at.isoformat()
        }
