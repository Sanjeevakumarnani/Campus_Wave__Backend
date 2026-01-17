from app.extensions import db
from datetime import datetime
import enum

class Admin(db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    profile_picture = db.Column(db.String(255), nullable=True)
    admin_type = db.Column(db.String(20), default="ADMIN") # MAIN_ADMIN or ADMIN
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        # Handle profile_picture path
        pp_value = self.profile_picture
        if pp_value and not pp_value.startswith('/') and not pp_value.startswith('http'):
            pp_value = f"/uploads/profiles/{pp_value}"
            
        return {
            'name': self.name,
            'profile_picture': pp_value,
            'admin_type': self.admin_type,
            'created_at': self.created_at.isoformat()
        }
