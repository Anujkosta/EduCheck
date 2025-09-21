from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, abort
from models import db, Teacher, Assignment, Submission
from models import Student
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from datetime import datetime as dt
from werkzeug.security import generate_password_hash, check_password_hash

# Import plagiarism checker
from plagiarism.plagiarism_checker import (
    extract_text,
    check_file_plagiarism,
    check_text_plagiarism
)
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
# AI detection
from utils.ai_detection import detect_ai_content

# -------------------
# App Configuration
# -------------------
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
UPLOAD_FOLDER = "uploads"
REPORT_FOLDER = "reports"
ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "txt", "png", "jpg", "jpeg"}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB limit
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(REPORT_FOLDER, exist_ok=True)

# Initialize db with app
db.init_app(app)

# -------------------
# Student Auth Routes
# -------------------
@app.route("/student/signup", methods=["GET", "POST"])
def student_signup():
    error = None
    if request.method == "POST":
        name = request.form["name"]
        reg_no = request.form["reg_no"]
        email = request.form["email"]
        password = request.form["password"]
        if Student.query.filter((Student.email == email) | (Student.reg_no == reg_no)).first():
            error = "Email or Registration Number already exists."
        else:
            hashed_pw = generate_password_hash(password)
            student = Student(name=name, reg_no=reg_no, email=email, password=hashed_pw)
            db.session.add(student)
            db.session.commit()
            return redirect(url_for("student_login"))
    return render_template("student_signup.html", error=error)

@app.route("/student/login", methods=["GET", "POST"])
def student_login():
    error = None
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        student = Student.query.filter_by(email=email).first()
        if student and check_password_hash(student.password, password):
            session["student_id"] = student.id
            return redirect(url_for("student_dashboard"))
        else:
            error = "Invalid email or password."
    return render_template("student_login.html", error=error)

@app.route("/student/logout")
def student_logout():
    session.pop("student_id", None)
    return redirect(url_for("student_login"))

# -------------------
# Student Dashboard Route
# -------------------
@app.route("/student/dashboard")
def student_dashboard():
    if "student_id" not in session:
        return redirect(url_for("student_login"))
    student = Student.query.get(session["student_id"])
    assignments = Assignment.query.order_by(Assignment.due_date.desc()).all()
    submissions = Submission.query.filter_by(student_id=student.id).all()
    # Map assignment_id to latest submission for quick lookup
    submitted_assignments = {}
    for sub in submissions:
        if sub.assignment_id not in submitted_assignments or sub.submitted_at > submitted_assignments[sub.assignment_id].submitted_at:
            submitted_assignments[sub.assignment_id] = sub
    # Prepare submission history for table
    submission_history = []
    for sub in submissions:
        submission_history.append({
            "id": sub.id,
            "assignment_title": sub.assignment.title,
            "submitted_at": sub.submitted_at.strftime("%d %b %Y %I:%M %p") if sub.submitted_at else "—",
            "is_late": sub.is_late,
            "file_path": sub.file_path,
            "feedback": getattr(sub, 'feedback', None)
        })
    return render_template(
        "student_dashboard.html",
        student=student,
        assignments=assignments,
        submitted_assignments=submitted_assignments,
        submissions=submission_history,
        now=dt.utcnow()
    )

# -------------------
# Helpers
# -------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_file_size(file):
    """Check if file size is within limits"""
    if hasattr(file, 'content_length'):
        return file.content_length <= MAX_FILE_SIZE
    return True

def sanitize_filename(filename):
    """Remove dangerous characters from filename"""
    import re
    # Remove any characters that aren't alphanumeric, dots, hyphens, or underscores
    filename = re.sub(r'[^\w\-_\.]', '', filename)
    # Ensure filename isn't empty and doesn't start with a dot
    if not filename or filename.startswith('.'):
        filename = 'file_' + filename
    return filename

def generate_report_pdf(submission, report_path=None):
    """Fallback report if highlight PDF is not available"""
    if report_path is None:
        report_path = submission.report_path

    c = canvas.Canvas(report_path, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(100, height - 50, "Plagiarism Report")

    c.setFont("Helvetica", 12)
    c.drawString(50, height - 100, f"Student: {submission.student_name} ({submission.reg_no})")
    c.drawString(50, height - 120, f"Email: {submission.student_email}")
    c.drawString(50, height - 140, f"Assignment: {submission.assignment.title}")
    c.drawString(50, height - 160, f"Submitted at: {submission.submitted_at.strftime('%Y-%m-%d %H:%M:%S')}")
    c.drawString(50, height - 180, f"Late: {'Yes' if submission.is_late else 'No'}")
    c.drawString(50, height - 200, f"Plagiarism Score: {submission.plagiarism}%")
    c.drawString(50, height - 220, f"AI Detected: {'Yes' if submission.ai_detected else 'No'}")

    c.showPage()
    c.save()

# -------------------
# Routes
# -------------------
@app.route("/")
def home():
    return redirect(url_for("login"))

@app.route("/signup", methods=["GET", "POST"])
def teacher_signup():
    error = None
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        
        if Teacher.query.filter_by(email=email).first():
            error = "Email already exists."
        else:
            hashed_pw = generate_password_hash(password)
            teacher = Teacher(name=name, email=email, password=hashed_pw)
            db.session.add(teacher)
            db.session.commit()
            return redirect(url_for("login"))
    return render_template("signup.html", error=error)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        teacher = Teacher.query.filter_by(email=email).first()
        if teacher and check_password_hash(teacher.password, password):
            session["teacher_id"] = teacher.id
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid email or password"
    return render_template("login.html", error=error)

@app.route("/create", methods=["GET", "POST"])
def create_assignment():
    if "teacher_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        due_date = datetime.strptime(request.form["due_date"], "%Y-%m-%dT%H:%M")
        assignment = Assignment(
            title=title,
            description=description,
            due_date=due_date,
            teacher_id=session["teacher_id"]
        )
        db.session.add(assignment)
        db.session.commit()
        return redirect(url_for("dashboard"))

    return render_template("creating_assignment.html")

@app.route("/submit/<int:assignment_id>", methods=["GET", "POST"])
def submit_assignment(assignment_id):
    assignment = Assignment.query.get_or_404(assignment_id)

    if request.method == "POST":
        student_name = request.form["student_name"]
        reg_no = request.form["reg_no"]
        email = request.form["email"]
        text_data = request.form.get("text_data")

        file = request.files.get("file")
        file_path = None
        file_ext = None
        if file and file.filename:
            if not allowed_file(file.filename):
                return render_template("submission_form.html", assignment=assignment, error="File type not allowed")
            if not validate_file_size(file):
                return render_template("submission_form.html", assignment=assignment, error="File too large (max 16MB)")
            
            # Sanitize filename and create secure path
            safe_filename = sanitize_filename(file.filename)
            filename = secure_filename(f"{assignment_id}_{reg_no}_{safe_filename}")
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)
            file_ext = os.path.splitext(filename)[1].lower()

        is_late = datetime.utcnow() > assignment.due_date

        plagiarism_score = 0
        highlight_report = None
        ai_detected = False

        # Run plagiarism check and AI detection
        if file_path:
            plagiarism_score, highlight_report = check_file_plagiarism(file_path)
            # If file is text-based, extract text for AI detection
            if file_ext in [".txt", ".doc", ".docx", ".pdf"]:
                try:
                    file_text = extract_text(file_path)
                    if file_text:
                        ai_detected = detect_ai_content(file_text)
                except Exception as e:
                    ai_detected = False
            else:
                ai_detected = False
        elif text_data:
            plagiarism_score, highlight_report = check_text_plagiarism(text_data)
            ai_detected = detect_ai_content(text_data)

        # Link submission to logged-in student if available
        student_id = session.get("student_id")
        submission = Submission(
            student_name=student_name,
            reg_no=reg_no,
            student_email=email,
            text_content=text_data if text_data else None,
            file_path=file_path,
            assignment_id=assignment.id,
            is_late=is_late,
            plagiarism=int(plagiarism_score),
            ai_detected=ai_detected,
            student_id=student_id
        )
        db.session.add(submission)
        db.session.commit()

        # Save plagiarism report
        if highlight_report and os.path.exists(highlight_report):
            report_path = os.path.join(REPORT_FOLDER, f"report_{assignment.id}_{submission.id}_{secure_filename(reg_no)}.pdf")
            # Use os.replace to overwrite if file exists
            os.replace(highlight_report, report_path)
            submission.report_path = report_path
        else:
            # fallback simple report
            report_filename = f"report_{assignment.id}_{submission.id}_{secure_filename(reg_no)}.pdf"
            report_path = os.path.join(REPORT_FOLDER, report_filename)
            generate_report_pdf(submission, report_path=report_path)
            submission.report_path = report_path

        db.session.commit()

        return render_template("submission_form.html", assignment=assignment, success=True, plagiarism=plagiarism_score, ai_detected=ai_detected)

    return render_template("submission_form.html", assignment=assignment)

@app.route("/download/<int:submission_id>")
def download_file(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    if submission.file_path and os.path.exists(submission.file_path):
        return send_from_directory(
            directory=os.path.dirname(submission.file_path),
            path=os.path.basename(submission.file_path),
            as_attachment=True
        )
    abort(404, description="File not found")

@app.route("/download-report/<int:submission_id>")
def download_report(submission_id):
    submission = Submission.query.get_or_404(submission_id)
    if submission.report_path and os.path.exists(submission.report_path):
        return send_from_directory(
            directory=os.path.dirname(submission.report_path),
            path=os.path.basename(submission.report_path),
            as_attachment=True
        )
    abort(404, description="Report not found")

# Teacher dashboard with grading/feedback form
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "teacher_id" not in session:
        return redirect(url_for("login"))

    # Handle grading/feedback POST
    if request.method == "POST":
        submission_id = request.form.get("submission_id")
        grade = request.form.get("grade")
        feedback = request.form.get("feedback")
        submission = Submission.query.get(submission_id)
        if submission:
            submission.grade = grade
            submission.feedback = feedback
            db.session.commit()

    assignments = Assignment.query.all()
    submissions = Submission.query.all()
    submission_list = [s.to_dict() for s in submissions]
    # Also pass Submission objects for form rendering
    return render_template(
        "dashboard_analytics.html",
        assignments=assignments,
        submissions=submission_list,
        submission_objs=submissions
    )

@app.route("/logout")
def logout():
    session.pop("teacher_id", None)
    return redirect(url_for("login"))

# -------------------
# Error Handlers
# -------------------
@app.errorhandler(413)
def too_large(e):
    return render_template('error.html', 
                         error_code=413, 
                         error_message="File too large. Maximum size is 16MB."), 413

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', 
                         error_code=404, 
                         error_message="Page not found."), 404

@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    return render_template('error.html', 
                         error_code=500, 
                         error_message="Internal server error."), 500

# -------------------
# Init
# -------------------
if __name__ == "__main__":
    if not os.path.exists("app.db"):
        with app.app_context():
            db.create_all()
            print("✅ Database created.")
    app.run(debug=True)
