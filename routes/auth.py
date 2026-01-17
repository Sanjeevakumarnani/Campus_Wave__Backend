from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.extensions import db
from app.models.user import User, UserRole
from app.models.student import Student
from app.models.admin import Admin
from app.models.admin_request import AdminRequest, RequestStatus
from app.utils.email import send_otp_email
from app.utils.password_validator import validate_password
from werkzeug.security import generate_password_hash
from datetime import datetime

bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    
    # Validate required fields
    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'error': 'Email, password, and name are required'}), 400
    
    # Check if user already exists by email
    email = data['email'].lower()
    existing_user_email = User.query.filter_by(email=email).first()
    if existing_user_email:
        if existing_user_email.is_verified:
            return jsonify({'error': 'Email already registered and verified'}), 409
        else:
            # User exists but is unverified, allow re-registration by deleting old record
            db.session.delete(existing_user_email)
            db.session.commit()
            
    # Check if phone number already exists
    if data.get('phone_number'):
        existing_user_phone = User.query.filter_by(phone_number=data['phone_number']).first()
        if existing_user_phone:
            if existing_user_phone.is_verified:
                return jsonify({'error': 'Phone number already registered and verified'}), 409
            else:
                # Phone exists but is unverified, allow re-registration by deleting old record
                db.session.delete(existing_user_phone)
                db.session.commit()
    
    # Validate password strength
    is_valid, errors = validate_password(
        password=data['password'],
        name=data['name'],
        email=email,
        phone=data.get('phone_number')
    )
    if not is_valid:
        return jsonify({'error': errors[0] if errors else 'Password does not meet requirements'}), 400
    
    # ADMIN-LOCKED: Admin registration permanently disabled
    if data.get('role') == 'ADMIN':
        return jsonify({
            'error': 'Admin registration is disabled. Only one admin exists.',
            'code': 'ADMIN_REGISTRATION_DISABLED'
        }), 403

    # Create new student user
    user = User(
        email=email,
        phone_number=data.get('phone_number'),
        role=UserRole.STUDENT
    )
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.flush() # Get user.id
    
    # Create profile
    profile = Student(
        id=user.id,
        name=data['name'],
        college_pin=data.get('college_pin')
    )
    
    db.session.add(profile)
    db.session.commit()
    
    # Generate OTP
    import random
    from datetime import datetime, timedelta
    from app.models.otp import OTP
    
    otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    
    otp = OTP(identifier=user.email, expires_at=expires_at)
    otp.set_otp(otp_code)
    db.session.add(otp)
    db.session.commit()
    
    # SEND GMAIL OTP
    send_otp_email(user.email, otp_code)
    
    return jsonify({
        'message': 'Registration successful. Please verify your OTP.',
        'verification_required': True,
        'email': user.email
    }), 201

@bp.route('/login', methods=['POST'])
def login():
    """Login user and return JWT token"""
    data = request.get_json()
    
    # Validate required fields
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400
    
    # Find user
    email = data['email'].lower()
    user = User.query.filter_by(email=email).first()
    
    # Verify credentials
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401
        
    # Check verification status
    if not user.is_verified:
        return jsonify({
            'error': 'Account not verified',
            'verification_required': True,
            'email': user.email
        }), 403
    
    # Create access token (identity must be string for proper subject claim)
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        'access_token': access_token,
        'user': user.to_dict()
    }), 200

@bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user information"""
    user_id = int(get_jwt_identity())  # Convert string back to int
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(user.to_dict()), 200

@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user (client should delete token)"""
    return jsonify({'message': 'Logged out successfully'}), 200

@bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    """Verify OTP and return JWT token"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('otp'):
        return jsonify({'error': 'Email and OTP are required'}), 400
        
    from app.models.otp import OTP
    from datetime import datetime
    
    # Check for valid OTP
    email = data['email'].lower()
    otp_record = OTP.query.filter_by(identifier=email).order_by(OTP.created_at.desc()).first()
    
    if not otp_record or not otp_record.is_valid():
        return jsonify({'error': 'Invalid, expired, or blocked OTP. Please request a new one.'}), 400
        
    # Increment attempts
    otp_record.attempts += 1
    db.session.commit()
    
    if not otp_record.check_otp(data['otp']):
        if otp_record.attempts >= 3:
            return jsonify({'error': 'Too many failed attempts. This OTP is now invalid.'}), 400
        return jsonify({'error': f'Invalid OTP. {3 - otp_record.attempts} attempts remaining.'}), 400
        
    # Mark user as verified
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    user.is_verified = True
    
    # Delete used OTP
    db.session.delete(otp_record)
    db.session.commit()
    
    # Login successful
    access_token = create_access_token(identity=str(user.id))
    
    return jsonify({
        'message': 'Verification successful',
        'access_token': access_token,
        'user': user.to_dict()
    }), 200

@bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    """Resend OTP"""
    data = request.get_json()
    
    if not data or not data.get('email'):
        return jsonify({'error': 'Email is required'}), 400
        
    email = data['email'].lower()
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    if user.is_verified:
        return jsonify({'message': 'User already verified'}), 200
        
    # Generate new OTP
    import random
    from datetime import datetime, timedelta
    from app.models.otp import OTP
    
    otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    
    # Delete old OTPs for this user
    OTP.query.filter_by(identifier=user.email).delete()
    
    otp = OTP(identifier=user.email, expires_at=expires_at)
    otp.set_otp(otp_code)
    db.session.add(otp)
    db.session.commit()
    
    # SEND GMAIL OTP
    send_otp_email(user.email, otp_code)
    
    return jsonify({
        'message': 'OTP resent successfully'
    }), 200

@bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Send OTP for password reset"""
    data = request.get_json()
    if not data or not data.get('email'):
        return jsonify({'error': 'Email is required'}), 400
        
    email = data['email'].lower()
    user = User.query.filter_by(email=email).first()
    if not user:
        # For security, we might want to say "check email" even if not found, 
        # but user flow says "show error if not exists"
        return jsonify({'error': 'Email not found in our records'}), 404
        
    # Generate OTP
    import random
    from datetime import datetime, timedelta
    from app.models.otp import OTP
    
    otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    
    # Delete old OTPs for this user
    OTP.query.filter_by(identifier=user.email).delete()
    
    otp = OTP(identifier=user.email, expires_at=expires_at)
    otp.set_otp(otp_code)
    db.session.add(otp)
    db.session.commit()
    
    # Send Email
    send_otp_email(user.email, otp_code)
    
    return jsonify({
        'message': 'OTP sent to your email for password reset'
    }), 200

@bp.route('/verify-reset-otp', methods=['POST'])
def verify_reset_otp():
    """Verify OTP for password reset without changing it yet"""
    data = request.get_json()
    if not data or not data.get('email') or not data.get('otp'):
        return jsonify({'error': 'Email and OTP are required'}), 400
        
    from app.models.otp import OTP
    email = data['email'].lower()
    otp_record = OTP.query.filter_by(identifier=email).order_by(OTP.created_at.desc()).first()
    
    if not otp_record or not otp_record.is_valid():
        return jsonify({'error': 'Invalid, expired, or blocked OTP'}), 400
        
    # Increment attempts
    otp_record.attempts += 1
    db.session.commit()
    
    if not otp_record.check_otp(data['otp']):
        if otp_record.attempts >= 3:
            return jsonify({'error': 'Too many failed attempts. This OTP is now invalid.'}), 400
        return jsonify({'error': f'Invalid OTP. {3 - otp_record.attempts} attempts remaining.'}), 400
        
    return jsonify({'message': 'OTP verified successfully. Proceed to reset password.'}), 200

@bp.route('/reset-password', methods=['POST'])
def reset_password():
    """Reset password after OTP verification"""
    data = request.get_json()
    if not data or not data.get('email') or not data.get('otp') or not data.get('password'):
        return jsonify({'error': 'Email, OTP, and new password are required'}), 400
        
    from app.models.otp import OTP
    email = data['email'].lower()
    otp_record = OTP.query.filter_by(identifier=email).order_by(OTP.created_at.desc()).first()
    
    if not otp_record or not otp_record.is_valid():
        return jsonify({'error': 'Invalid or expired OTP'}), 400
        
    if not otp_record.check_otp(data['otp']):
        return jsonify({'error': 'Invalid OTP'}), 400
        
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Validate new password strength
    is_valid, errors = validate_password(
        password=data['password'],
        name=user.name,
        email=email
    )
    if not is_valid:
        return jsonify({'error': errors[0] if errors else 'Password does not meet requirements'}), 400
        
    # Reset Password
    user.set_password(data['password'])
    
    # Delete OTP
    db.session.delete(otp_record)
    db.session.commit()
    
    return jsonify({'message': 'Password reset successful. Please log in.'}), 200

@bp.route('/profile', methods=['PATCH'])
@jwt_required()
def update_profile():
    """Update user profile information"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    
    # Update allowed fields based on profile
    if user.role == UserRole.STUDENT:
        profile = user.student_profile
        if not profile:
            profile = Student(id=user.id)
            db.session.add(profile)
    else:
        profile = user.admin_profile
        if not profile:
            profile = Admin(id=user.id, admin_type=user.role.value)
            db.session.add(profile)

    if data.get('name'):
        profile.name = data['name']
    
    if user.role == UserRole.STUDENT and data.get('college_pin'):
        profile.college_pin = data['college_pin']
    
    db.session.commit()
    
    return jsonify(user.to_dict()), 200

@bp.route('/profile/picture', methods=['POST'])
@jwt_required()
def upload_profile_picture():
    """Upload user profile picture"""
    import os
    from werkzeug.utils import secure_filename
    
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if 'picture' not in request.files:
        return jsonify({'error': 'No picture file provided'}), 400
    
    file = request.files['picture']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Validate file extension
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    file_ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if file_ext not in allowed_extensions:
        return jsonify({'error': 'Invalid file type. Allowed: png, jpg, jpeg, gif, webp'}), 400
    
    # Create profiles upload directory if it doesn't exist
    upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'profiles')
    os.makedirs(upload_folder, exist_ok=True)
    
    # Generate unique filename
    filename = f"profile_{user_id}_{int(datetime.now().timestamp())}.{file_ext}"
    filepath = os.path.join(upload_folder, filename)
    
    # Delete old profile picture if exists
    if user.profile_picture:
        old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], user.profile_picture.replace('/uploads/', '', 1))
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except:
                pass  # Ignore deletion errors
    
    # Save new file
    file.save(filepath)
    
    # Update profile picture path in appropriate profile table
    profile_path = f"/uploads/profiles/{filename}"
    
    if user.role == UserRole.STUDENT:
        if not user.student_profile:
            user.student_profile = Student(id=user.id)
        user.student_profile.profile_picture = profile_path
    else:
        if not user.admin_profile:
            user.admin_profile = Admin(id=user.id, admin_type=user.role.value)
        user.admin_profile.profile_picture = profile_path
        
    db.session.commit()
    
    return jsonify({
        'message': 'Profile picture uploaded successfully',
        'profile_picture': profile_path
    }), 200

@bp.route('/admin-requests', methods=['GET'])
@jwt_required()
def get_admin_requests():
    """Get all pending admin registration requests (Main Admin only)"""
    # ADMIN-LOCKED: Admin approval feature permanently disabled
    return jsonify({
        'error': 'Admin requests feature is disabled.',
        'code': 'FEATURE_DISABLED'
    }), 403

@bp.route('/approve-admin/<int:request_id>', methods=['POST'])
@jwt_required()
def approve_admin(request_id):
    """Approve or reject an admin registration request (Main Admin only)"""
    # ADMIN-LOCKED: Admin approval feature permanently disabled
    return jsonify({
        'error': 'Admin approval is disabled. Feature locked.',
        'code': 'FEATURE_DISABLED'
    }), 403
