from app.extensions import db
from datetime import datetime

class Student(db.Model):
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    profile_picture = db.Column(db.String(255), nullable=True)
    college_pin = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        # Handle profile_picture path
        pp_value = self.profile_picture
        if pp_value and not pp_value.startswith('/') and not pp_value.startswith('http'):
            pp_value = f"/uploads/profiles/{pp_value}"
            
        return {
            'name': self.name,
            'profile_picture': pp_value,
            'college_pin': self.college_pin,
            'created_at': self.created_at.isoformat()
        }
