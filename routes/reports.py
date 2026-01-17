"""
API routes for Problem Reporting System.

Students can report college-related problems.
Admins can view, filter, update status, and send replies.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from app.extensions import db
from app.models.report import Report, ReportCategory, ReportPriority, ReportStatus
from app.models.radio import Radio
from app.models.user import User, UserRole
from app.middleware.auth import admin_required
from app.utils.upload import save_upload, allowed_file

bp = Blueprint('reports', __name__, url_prefix='/api/reports')


@bp.route('', methods=['POST'])
@jwt_required()
def create_report():
    """Submit a problem report (student)"""
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    # Validate required fields
    category = data.get('category', '').upper()
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    priority = data.get('priority', 'MEDIUM').upper()
    
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    
    if not category:
        return jsonify({'error': 'Category is required'}), 400
    
    # Validate enums
    try:
        category_enum = ReportCategory[category]
    except KeyError:
        return jsonify({
            'error': 'Invalid category. Use: ACADEMIC, FACILITIES, TECHNICAL, or OTHER'
        }), 400
    
    try:
        priority_enum = ReportPriority[priority]
    except KeyError:
        return jsonify({'error': 'Invalid priority. Use: LOW, MEDIUM, or HIGH'}), 400
    
    # Optional session_id and image_url
    session_id = data.get('session_id')
    image_url = data.get('image_url', '').strip()
    
    # Verify session exists if provided
    if session_id:
        radio = Radio.query.get(session_id)
        if not radio:
            return jsonify({'error': 'Radio session not found'}), 404
    
    try:
        new_report = Report(
            student_id=user_id,
            session_id=session_id,
            category=category_enum,
            title=title,
            description=description,
            image_url=image_url if image_url else None,
            priority=priority_enum,
            status=ReportStatus.PENDING
        )
        
        db.session.add(new_report)
        db.session.commit()
        
        return jsonify({
            'message': 'Report submitted successfully',
            'report': new_report.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to submit report: {str(e)}'}), 500


@bp.route('/<int:report_id>/upload-image', methods=['POST'])
@jwt_required()
def upload_report_image(report_id):
    """Upload image for a report"""
    user_id = int(get_jwt_identity())
    
    report = Report.query.get(report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    
    # Only report owner can upload image
    if report.student_id != user_id:
        return jsonify({'error': 'Unauthorized. You can only upload images to your own reports'}), 403
    
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename, allowed_extensions=['png', 'jpg', 'jpeg', 'gif', 'webp']):
        return jsonify({'error': 'Invalid file type. Only images allowed'}), 400
    
    try:
        # Save to reports subdirectory
        filepath = save_upload(file, subdirectory='reports')
        report.image_url = filepath
        db.session.commit()
        
        return jsonify({
            'message': 'Image uploaded successfully',
            'image_url': filepath
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


@bp.route('', methods=['GET'])
@jwt_required()
def get_reports():
    """Get reports (admin: all with filters, student: own reports only)"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    
    query = Report.query
    
    # Students can only see their own reports
    if user.role != UserRole.ADMIN:
        query = query.filter_by(student_id=user_id)
    else:
        # Admin filters
        status_filter = request.args.get('status')
        category_filter = request.args.get('category')
        priority_filter = request.args.get('priority')
        
        if status_filter:
            try:
                status_enum = ReportStatus[status_filter.upper()]
                query = query.filter_by(status=status_enum)
            except KeyError:
                pass
        
        if category_filter:
            try:
                category_enum = ReportCategory[category_filter.upper()]
                query = query.filter_by(category=category_enum)
            except KeyError:
                pass
        
        if priority_filter:
            try:
                priority_enum = ReportPriority[priority_filter.upper()]
                query = query.filter_by(priority=priority_enum)
            except KeyError:
                pass
    
    # Order by priority (HIGH first) then by created_at descending
    priority_order = db.case(
        (Report.priority == ReportPriority.HIGH, 1),
        (Report.priority == ReportPriority.MEDIUM, 2),
        (Report.priority == ReportPriority.LOW, 3),
        else_=4
    )
    
    query = query.order_by(priority_order, Report.created_at.desc())
    
    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    
    return jsonify({
        'reports': [r.to_dict() for r in pagination.items],
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    }), 200


@bp.route('/<int:report_id>', methods=['GET'])
@jwt_required()
def get_report(report_id):
    """Get single report details"""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    
    report = Report.query.get(report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    
    # Check authorization
    if user.role != UserRole.ADMIN and report.student_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify(report.to_dict()), 200


@bp.route('/<int:report_id>/status', methods=['PUT'])
@admin_required
def update_report_status(current_user_id, report_id):
    """Update report status (admin only)"""
    data = request.get_json()
    new_status = data.get('status', '').upper()
    
    if not new_status:
        return jsonify({'error': 'Status is required'}), 400
    
    try:
        status_enum = ReportStatus[new_status]
    except KeyError:
        return jsonify({
            'error': 'Invalid status. Use: PENDING, IN_PROGRESS, or RESOLVED'
        }), 400
    
    report = Report.query.get(report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    
    report.status = status_enum
    db.session.commit()
    
    return jsonify({
        'message': 'Report status updated successfully',
        'report': report.to_dict()
    }), 200


@bp.route('/<int:report_id>/reply', methods=['POST'])
@admin_required
def send_admin_reply(current_user_id, report_id):
    """Send admin reply to a report (admin only)"""
    data = request.get_json()
    reply = data.get('reply', '').strip()
    
    if not reply:
        return jsonify({'error': 'Reply message is required'}), 400
    
    report = Report.query.get(report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    
    report.admin_reply = reply
    db.session.commit()
    
    # TODO: Send notification to student
    # (Can be implemented later using the notification system)
    
    return jsonify({
        'message': 'Reply sent successfully',
        'report': report.to_dict()
    }), 200
