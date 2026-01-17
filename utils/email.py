from threading import Thread
from flask_mail import Message
from app.extensions import mail
from flask import current_app
from datetime import datetime

def send_async_email(app, msg):
    with app.app_context():
        start_time = datetime.now()
        try:
            with open("email_log.txt", "a") as f:
                f.write(f"[{start_time}] Starting to send email to {msg.recipients}...\n")
            mail.send(msg)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            with open("email_log.txt", "a") as f:
                f.write(f"[{end_time}] Successfully sent email to {msg.recipients} (took {duration:.2f}s)\n")
        except Exception as e:
            end_time = datetime.now()
            with open("email_log.txt", "a") as f:
                f.write(f"[{end_time}] Error sending email to {msg.recipients}: {e}\n")

def send_otp_email(email, otp):
    """Send OTP to user email asynchronously"""
    app = current_app._get_current_object()
    msg = Message(
        subject="CampusWave - Your Verification Code",
        recipients=[email],
        body=f"Your verification code is: {otp}\n\nThis code will expire in 10 minutes."
    )
    Thread(target=send_async_email, args=(app, msg)).start()
    return True

def send_suggestion_approved_email(email, student_name, radio_title):
    """Send suggestion approval email asynchronously"""
    app = current_app._get_current_object()
    msg = Message(
        subject="CampusWave - Suggestion Accepted! 🎉",
        recipients=[email],
        body=f"Hi {student_name},\n\nGreat news! Your suggestion '{radio_title}' has been reviewed and accepted by the admin.\n\nThank you for your valuable feedback regarding this radio show!\n\nBest regards,\nCampusWave Team"
    )
    Thread(target=send_async_email, args=(app, msg)).start()
    return True

def send_admin_approval_email(email, name):
    """Send admin approval notification email asynchronously"""
    app = current_app._get_current_object()
    msg = Message(
        subject="Admin Request Approved - CampusWave",
        recipients=[email],
        body=f"Hello {name},\n\nYour request to register as an Admin has been accepted by the Main Admin.\n\nYou can now log in to the Admin Dashboard using your registered email and password.\n\nThank you.\nCampusWave Team"
    )
    Thread(target=send_async_email, args=(app, msg)).start()
    return True
