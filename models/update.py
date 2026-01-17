from app.extensions import db
from datetime import datetime
import enum

class UpdateCategory(enum.Enum):
    COLLEGE = "COLLEGE"
    CLUB = "CLUB"
    MOTIVATION = "MOTIVATION"

class MediaType(enum.Enum):
    NONE = "NONE"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"

class Update(db.Model):
    __tablename__ = 'updates'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    media_url = db.Column(db.String(255))
    media_type = db.Column(db.Enum(MediaType), default=MediaType.NONE)
    category = db.Column(db.Enum(UpdateCategory), nullable=False)
    is_pinned = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_dict(self, current_user_id=None):
        """Convert to dictionary for JSON response"""
        from app.models.user import User
        from app.models.update_like import UpdateLike
        from app.models.update_reaction import UpdateReaction
        
        creator = User.query.get(self.created_by)
        
        # Handle media_url
        media_url_value = None
        if self.media_url and len(self.media_url.strip()) > 0:
            if self.media_url.startswith('/'):
                media_url_value = self.media_url
            else:
                media_url_value = f'/uploads/{self.media_url}'
        
        # Handle creator profile picture
        creator_profile = None
        if creator and creator.profile_picture:
            if creator.profile_picture.startswith('/'):
                creator_profile = creator.profile_picture
            else:
                creator_profile = f'/uploads/{creator.profile_picture}'
        
        # Likes logic
        likes_count = UpdateLike.query.filter_by(update_id=self.id).count()
        is_liked = False
        if current_user_id:
            is_liked = UpdateLike.query.filter_by(user_id=current_user_id, update_id=self.id).first() is not None
        
        # Reactions (replacing comments)
        reactions = UpdateReaction.get_reaction_counts(self.id)
        user_reaction = None
        if current_user_id:
            user_reaction_obj = UpdateReaction.query.filter_by(
                user_id=current_user_id,
                update_id=self.id
            ).first()
            if user_reaction_obj:
                user_reaction = user_reaction_obj.emoji
        
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'media_url': media_url_value,
            'media_type': self.media_type.value if self.media_type else 'NONE',
            'category': self.category.value if self.category else None,
            'is_pinned': self.is_pinned,
            'created_by': self.created_by,
            'creator_name': creator.name if creator else None,
            'creator_profile': creator_profile,
            'likes_count': likes_count,
            'is_liked': is_liked,
            'reactions': reactions,
            'user_reaction': user_reaction,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<Update {self.title}>'
