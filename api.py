from flask import Blueprint, request, jsonify, session
from models import db, Teacher, Student, Assignment, Submission
from werkzeug.security import check_password_hash
from datetime import datetime
import os

api = Blueprint('api', __name__, url_prefix='/api')

def require_auth():
    """Check if user is authenticated"""
    if 'teacher_id' not in session and 'student_id' not in session:
        return jsonify({'error': 'Authentication required'}), 401
    return None

@api.route('/auth/login', methods=['POST'])
def api_login():
    """API endpoint for user login"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    user_type = data.get('user_type', 'teacher')  # 'teacher' or 'student'
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    if user_type == 'teacher':
        user = Teacher.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['teacher_id'] = user.id
            return jsonify({
                'success': True,
                'user_type': 'teacher',
                'user_id': user.id,
                'name': user.name,
                'email': user.email
            })
    else:
        user = Student.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['student_id'] = user.id
            return jsonify({
                'success': True,
                'user_type': 'student',
                'user_id': user.id,
                'name': user.name,
                'email': user.email,
                'reg_no': user.reg_no
            })
    
    return jsonify({'error': 'Invalid credentials'}), 401

@api.route('/auth/logout', methods=['POST'])
def api_logout():
    """API endpoint for user logout"""
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@api.route('/assignments', methods=['GET'])
def get_assignments():
    """Get all assignments"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    assignments = Assignment.query.order_by(Assignment.due_date.desc()).all()
    return jsonify([{
        'id': a.id,
        'title': a.title,
        'description': a.description,
        'due_date': a.due_date.isoformat(),
        'created_at': a.created_at.isoformat(),
        'teacher_id': a.teacher_id
    } for a in assignments])

@api.route('/assignments/<int:assignment_id>', methods=['GET'])
def get_assignment(assignment_id):
    """Get specific assignment"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    assignment = Assignment.query.get_or_404(assignment_id)
    return jsonify({
        'id': assignment.id,
        'title': assignment.title,
        'description': assignment.description,
        'due_date': assignment.due_date.isoformat(),
        'created_at': assignment.created_at.isoformat(),
        'teacher_id': assignment.teacher_id
    })

@api.route('/submissions', methods=['GET'])
def get_submissions():
    """Get all submissions (teachers only)"""
    if 'teacher_id' not in session:
        return jsonify({'error': 'Teacher access required'}), 403
    
    submissions = Submission.query.all()
    return jsonify([submission.to_dict() for submission in submissions])

@api.route('/submissions/<int:submission_id>', methods=['GET'])
def get_submission(submission_id):
    """Get specific submission"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    submission = Submission.query.get_or_404(submission_id)
    
    # Check permissions
    if 'student_id' in session and submission.student_id != session['student_id']:
        return jsonify({'error': 'Access denied'}), 403
    
    return jsonify(submission.to_dict())

@api.route('/submissions', methods=['POST'])
def create_submission():
    """Create new submission"""
    if 'student_id' not in session:
        return jsonify({'error': 'Student access required'}), 403
    
    data = request.get_json()
    assignment_id = data.get('assignment_id')
    text_content = data.get('text_content')
    
    if not assignment_id:
        return jsonify({'error': 'Assignment ID required'}), 400
    
    assignment = Assignment.query.get_or_404(assignment_id)
    student = Student.query.get(session['student_id'])
    
    is_late = datetime.utcnow() > assignment.due_date
    
    submission = Submission(
        student_name=student.name,
        reg_no=student.reg_no,
        student_email=student.email,
        text_content=text_content,
        assignment_id=assignment_id,
        is_late=is_late,
        student_id=student.id
    )
    
    db.session.add(submission)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'submission_id': submission.id,
        'message': 'Submission created successfully'
    }), 201

@api.route('/submissions/<int:submission_id>/grade', methods=['PUT'])
def grade_submission(submission_id):
    """Grade a submission (teachers only)"""
    if 'teacher_id' not in session:
        return jsonify({'error': 'Teacher access required'}), 403
    
    data = request.get_json()
    grade = data.get('grade')
    feedback = data.get('feedback', '')
    
    submission = Submission.query.get_or_404(submission_id)
    submission.grade = grade
    submission.feedback = feedback
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Submission graded successfully'
    })

@api.route('/students/<int:student_id>/submissions', methods=['GET'])
def get_student_submissions(student_id):
    """Get submissions for a specific student"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    # Check permissions
    if 'student_id' in session and student_id != session['student_id']:
        return jsonify({'error': 'Access denied'}), 403
    
    submissions = Submission.query.filter_by(student_id=student_id).all()
    return jsonify([submission.to_dict() for submission in submissions])

@api.route('/analytics/overview', methods=['GET'])
def get_analytics_overview():
    """Get analytics overview (teachers only)"""
    if 'teacher_id' not in session:
        return jsonify({'error': 'Teacher access required'}), 403
    
    total_assignments = Assignment.query.count()
    total_submissions = Submission.query.count()
    late_submissions = Submission.query.filter_by(is_late=True).count()
    high_plagiarism = Submission.query.filter(Submission.plagiarism > 50).count()
    ai_detected = Submission.query.filter_by(ai_detected=True).count()
    
    return jsonify({
        'total_assignments': total_assignments,
        'total_submissions': total_submissions,
        'late_submissions': late_submissions,
        'high_plagiarism': high_plagiarism,
        'ai_detected': ai_detected,
        'on_time_rate': round((total_submissions - late_submissions) / total_submissions * 100, 2) if total_submissions > 0 else 0
    })

@api.route('/files/<int:submission_id>/download', methods=['GET'])
def download_submission_file(submission_id):
    """Download submission file"""
    auth_error = require_auth()
    if auth_error:
        return auth_error
    
    submission = Submission.query.get_or_404(submission_id)
    
    # Check permissions
    if 'student_id' in session and submission.student_id != session['student_id']:
        return jsonify({'error': 'Access denied'}), 403
    
    if not submission.file_path or not os.path.exists(submission.file_path):
        return jsonify({'error': 'File not found'}), 404
    
    return jsonify({
        'file_path': submission.file_path,
        'filename': os.path.basename(submission.file_path),
        'download_url': f'/download/{submission_id}'
    })
