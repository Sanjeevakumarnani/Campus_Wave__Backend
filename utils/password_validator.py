"""
Password validation utility for strong password enforcement.
"""
import re
from typing import Tuple, List, Optional

# Password rules
MIN_LENGTH = 8
SPECIAL_CHARS = set('@#$%!&*^()-_+=[]{}|\\/?<>,. ~`')

def validate_password(
    password: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None
) -> Tuple[bool, List[str]]:
    """
    Validate a password against strong password rules.
    
    Returns:
        Tuple of (is_valid, list_of_error_messages)
    """
    errors = []
    
    # Check minimum length
    if len(password) < MIN_LENGTH:
        errors.append(f"Password must be at least {MIN_LENGTH} characters long.")
    
    # Check for uppercase letter
    if not re.search(r'[A-Z]', password):
        errors.append("Include at least one uppercase letter (A-Z).")
    
    # Check for lowercase letter
    if not re.search(r'[a-z]', password):
        errors.append("Include at least one lowercase letter (a-z).")
    
    # Check for number
    if not re.search(r'[0-9]', password):
        errors.append("Include at least one number (0-9).")
    
    # Check for special character
    if not any(char in SPECIAL_CHARS for char in password):
        errors.append("Include at least one special character (@ # $ % ! & *).")
    
    # Check for spaces
    if ' ' in password:
        errors.append("Password cannot contain spaces.")
    
    # Check against user info (DISABLED)
    # if contains_user_info(password, name, email, phone):
    #     errors.append("Password cannot match your name, email, or phone number.")
    
    return (len(errors) == 0, errors)


def contains_user_info(
    password: str,
    name: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None
) -> bool:
    """
    Check if password contains user identifying information.
    """
    password_lower = password.lower()
    
    # Check name (if at least 3 chars to avoid false positives)
    if name:
        name_parts = [part for part in name.lower().split() if len(part) >= 3]
        for part in name_parts:
            if part in password_lower:
                return True
    
    # Check email prefix (before @)
    if email:
        email_prefix = email.split('@')[0].lower()
        if len(email_prefix) >= 3 and email_prefix in password_lower:
            return True
    
    # Check phone number (if at least 6 digits)
    if phone:
        phone_digits = ''.join(filter(str.isdigit, phone))
        if len(phone_digits) >= 6 and phone_digits in password:
            return True
    
    return False


def get_password_strength(password: str) -> str:
    """
    Get password strength level.
    
    Returns: 'weak', 'medium', or 'strong'
    """
    score = 0
    
    if len(password) >= MIN_LENGTH:
        score += 1
    if re.search(r'[A-Z]', password):
        score += 1
    if re.search(r'[a-z]', password):
        score += 1
    if re.search(r'[0-9]', password):
        score += 1
    if any(char in SPECIAL_CHARS for char in password):
        score += 1
    if ' ' not in password:
        score += 1
    
    if score <= 3:
        return 'weak'
    elif score <= 5:
        return 'medium'
    else:
        return 'strong'
