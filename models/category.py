from app.extensions import db
from datetime import datetime


class Category(db.Model):
    """Radio category model"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    color = db.Column(db.String(7), default='#5E72E4')  # Hex color
    icon = db.Column(db.String(50), default='radio')  # Icon name
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationship
    radios = db.relationship('Radio', back_populates='category', lazy='dynamic', foreign_keys='Radio.category_id')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'icon': self.icon
        }
