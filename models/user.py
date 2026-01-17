from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import enum

class UserRole(enum.Enum):
    MAIN_ADMIN = "MAIN_ADMIN"
    ADMIN = "ADMIN"
    STUDENT = "STUDENT"

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    
    # Relationships
    student_profile = db.relationship('Student', backref='user', uselist=False, cascade="all, delete-orphan")
    admin_profile = db.relationship('Admin', backref='user', uselist=False, cascade="all, delete-orphan")
    
    # Existing relationships for radios and suggestions
    created_radios = db.relationship('Radio', backref='creator', lazy='dynamic', foreign_keys='Radio.created_by')
    suggestions = db.relationship('RadioSuggestion', backref='student', lazy='dynamic', foreign_keys='RadioSuggestion.suggested_by')
    
    @property
    def name(self):
        if self.role == UserRole.STUDENT and self.student_profile:
            return self.student_profile.name
        if self.role in [UserRole.ADMIN, UserRole.MAIN_ADMIN] and self.admin_profile:
            return self.admin_profile.name
        return None

    @property
    def profile_picture(self):
        if self.role == UserRole.STUDENT and self.student_profile:
            return self.student_profile.profile_picture
        if self.role in [UserRole.ADMIN, UserRole.MAIN_ADMIN] and self.admin_profile:
            return self.admin_profile.profile_picture
        return None

    @property
    def college_pin(self):
        if self.role == UserRole.STUDENT and self.student_profile:
            return self.student_profile.college_pin
        return None

    def set_password(self, password):
        """Hash and set password"""
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password, password)
    
    def to_dict(self):
        """Convert to dictionary for JSON response, merging profile data"""
        data = {
            'id': self.id,
            'email': self.email,
            'phone_number': self.phone_number,
            'is_verified': self.is_verified,
            'role': self.role.value
        }
        
        # Merge profile data if available
        if self.role == UserRole.STUDENT and self.student_profile:
            data.update(self.student_profile.to_dict())
        elif self.role in [UserRole.ADMIN, UserRole.MAIN_ADMIN] and self.admin_profile:
            data.update(self.admin_profile.to_dict())
            
        return data
    
    def __repr__(self):
        return f'<User {self.email} ({self.role.value})>'
