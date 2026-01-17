from app.extensions import db
from datetime import datetime

class RadioSubscription(db.Model):
    __tablename__ = 'radio_subscriptions'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    radio_id = db.Column(db.Integer, db.ForeignKey('radios.id'), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
