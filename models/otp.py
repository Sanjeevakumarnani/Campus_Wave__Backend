from app.extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class OTP(db.Model):
    __tablename__ = 'otps'

    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(120), nullable=False, index=True) # Email or Phone
    hashed_otp = db.Column(db.String(255), nullable=False)
    attempts = db.Column(db.Integer, default=0)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_otp(self, otp_code):
        self.hashed_otp = generate_password_hash(otp_code)

    def check_otp(self, otp_code):
        return check_password_hash(self.hashed_otp, otp_code)

    def is_valid(self):
        return datetime.utcnow() < self.expires_at and self.attempts < 3

    def __repr__(self):
        return f'<OTP {self.identifier}>'
