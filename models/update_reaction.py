from datetime import datetime
from app.extensions import db

# Allowed emoji reactions
ALLOWED_EMOJIS = ['👍', '❤️', '😂', '😮', '😢', '🔥']

class UpdateReaction(db.Model):
    __tablename__ = 'update_reactions'
    
    id = db.Column(db.Integer, primary_key=True)
    update_id = db.Column(db.Integer, db.ForeignKey('updates.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    emoji = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        from app.models.user import User
        
        user = User.query.get(self.user_id)
        
        return {
            'id': self.id,
            'update_id': self.update_id,
            'user_id': self.user_id,
            'user_name': user.name if user else None,
            'emoji': self.emoji,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @staticmethod
    def validate_emoji(emoji):
        """Validate if emoji is allowed"""
        return emoji in ALLOWED_EMOJIS
    
    @staticmethod
    def get_reaction_counts(update_id):
        """Get count of each emoji type for an update"""
        reactions = UpdateReaction.query.filter_by(update_id=update_id).all()
        
        counts = {emoji: 0 for emoji in ALLOWED_EMOJIS}
        for reaction in reactions:
            if reaction.emoji in counts:
                counts[reaction.emoji] += 1
        
        return counts
    
    def __repr__(self):
        return f'<UpdateReaction update={self.update_id} user={self.user_id} emoji={self.emoji}>'
