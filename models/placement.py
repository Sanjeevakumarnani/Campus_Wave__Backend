from app.extensions import db
from datetime import datetime

class Placement(db.Model):
    __tablename__ = 'placements'
    
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    application_link = db.Column(db.String(255))
    image_url = db.Column(db.String(255), nullable=True)  # For company logos / posters / results
    deadline = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_dict(self):
        # Handle image_url - add full path if relative
        image_url_value = None
        if self.image_url and len(self.image_url.strip()) > 0:
            if self.image_url.startswith('/'):
                image_url_value = self.image_url
            else:
                image_url_value = f'/uploads/{self.image_url}'
        
        return {
            'id': self.id,
            'company_name': self.company_name,
            'position': self.position,
            'description': self.description,
            'application_link': self.application_link,
            'image_url': image_url_value,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
