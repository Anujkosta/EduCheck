from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from datetime import datetime as dt
from werkzeug.security import generate_password_hash, check_password_hash

# Try to import optional dependencies
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("⚠️ ReportLab not available - PDF reports disabled")

try:
    from utils.ai_detection import detect_ai_content
    AI_DETECTION_AVAILABLE = True
except ImportError:
    AI_DETECTION_AVAILABLE = False
    print("⚠️ AI detection not available")

try:
    from utils.email_service import init_mail, send_feedback_notification, send_late_submission_alert, send_plagiarism_alert
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False
    print("⚠️ Email service not available")

try:
    from utils.file_preview import generate_file_preview, get_file_info
    FILE_PREVIEW_AVAILABLE = True
except ImportError:
    FILE_PREVIEW_AVAILABLE = False
    print("⚠️ File preview not available")

# Use the simple plagiarism checker that doesn't require OpenCV
try:
    from plagiarism.plagiarism_checker_simple import extract_text, check_file_plagiarism, check_text_plagiarism
    PLAGIARISM_AVAILABLE = True
    print("✅ Simple plagiarism detection available")
except ImportError as e:
    PLAGIARISM_AVAILABLE = False
    print(f"⚠️ Plagiarism detection not available: {e}")

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
db = SQLAlchemy(app)

# Initialize email service if available
if EMAIL_AVAILABLE:
    try:
        init_mail(app)
        print("✅ Email service initialized")
    except Exception as e:
        print(f"⚠️ Email service failed to initialize: {e}")
        EMAIL_AVAILABLE = False

# -------------------
# Models
# -------------------
class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teacher.id"), nullable=False)
    submissions = db.relationship("Submission", backref="assignment", lazy=True)

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    reg_no = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    submissions = db.relationship("Submission", backref="student", lazy=True)

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(120), nullable=False)
    student_email = db.Column(db.String(120), nullable=True)
    reg_no = db.Column(db.String(20), nullable=True)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_late = db.Column(db.Boolean, default=False)
    plagiarism = db.Column(db.Integer, default=0)
    ai_detected = db.Column(db.Boolean, default=False)
    file_path = db.Column(db.String(300), nullable=True)
    text_content = db.Column(db.Text, nullable=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey("assignment.id"), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=True)
    grade = db.Column(db.String(10), nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    report_path = db.Column(db.String(300), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "student_name": self.student_name,
            "student_email": self.student_email,
            "reg_no": self.reg_no,
            "submitted_at": self.submitted_at.strftime("%d %b %Y %I:%M %p") if self.submitted_at else None,
            "is_late": self.is_late,
            "plagiarism": self.plagiarism,
            "ai_detected": self.ai_detected,
            "file_path": self.file_path,
            "report_path": getattr(self, 'report_path', None),
            "assignment_id": self.assignment_id,
            "grade": self.grade,
            "feedback": self.feedback
        }

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
            "feedback": getattr(sub, 'feedback', None),
            "grade": getattr(sub, 'grade', None)
        })
    return render_template(
        "student_dashboard_complete.html",
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
    if not REPORTLAB_AVAILABLE:
        return
    
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
                return render_template("submission_form_complete.html", assignment=assignment, error="File type not allowed", now=dt.utcnow())
            if not validate_file_size(file):
                return render_template("submission_form_complete.html", assignment=assignment, error="File too large (max 16MB)", now=dt.utcnow())
            
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

        # Run plagiarism check and AI detection if available
        print(f"🔍 Running plagiarism check...")
        if PLAGIARISM_AVAILABLE and file_path:
            try:
                plagiarism_score, highlight_report = check_file_plagiarism(file_path)
                print(f"✅ Plagiarism check completed: {plagiarism_score}%")
            except Exception as e:
                print(f"❌ Plagiarism check failed: {e}")
                plagiarism_score = 0

        if AI_DETECTION_AVAILABLE:
            try:
                if file_path and file_ext in [".txt", ".doc", ".docx", ".pdf"]:
                    if PLAGIARISM_AVAILABLE:
                        file_text = extract_text(file_path)
                        if file_text:
                            ai_detected = detect_ai_content(file_text)
                elif text_data:
                    ai_detected = detect_ai_content(text_data)
            except Exception as e:
                print(f"❌ AI detection failed: {e}")
                ai_detected = False

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

        # Save plagiarism report if available
        if highlight_report and os.path.exists(highlight_report):
            report_path = os.path.join(REPORT_FOLDER, f"report_{assignment.id}_{submission.id}_{secure_filename(reg_no)}.pdf")
            os.replace(highlight_report, report_path)
            submission.report_path = report_path
        elif REPORTLAB_AVAILABLE:
            # Generate fallback report
            report_filename = f"report_{assignment.id}_{submission.id}_{secure_filename(reg_no)}.pdf"
            report_path = os.path.join(REPORT_FOLDER, report_filename)
            generate_report_pdf(submission, report_path=report_path)
            submission.report_path = report_path

        db.session.commit()

        # Send notifications if email is available
        if EMAIL_AVAILABLE:
            try:
                if is_late:
                    teacher = Teacher.query.get(assignment.teacher_id)
                    if teacher and teacher.email:
                        send_late_submission_alert(teacher.email, teacher.name, student_name, assignment.title)
                
                if plagiarism_score > 50:
                    teacher = Teacher.query.get(assignment.teacher_id)
                    if teacher and teacher.email:
                        send_plagiarism_alert(teacher.email, teacher.name, student_name, assignment.title, plagiarism_score)
            except Exception as e:
                print(f"❌ Email notification failed: {e}")

        return render_template("submission_form_complete.html", assignment=assignment, success=True, plagiarism=plagiarism_score, ai_detected=ai_detected, now=dt.utcnow())

    return render_template("submission_form_complete.html", assignment=assignment, now=dt.utcnow())

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

@app.route("/preview/<int:submission_id>")
def preview_file(submission_id):
    """Preview submitted file"""
    if not FILE_PREVIEW_AVAILABLE:
        return "<p>File preview not available</p>", 503
    
    submission = Submission.query.get_or_404(submission_id)
    
    if not submission.file_path or not os.path.exists(submission.file_path):
        return "<p>File not found</p>", 404
    
    preview_html = generate_file_preview(submission.file_path)
    file_info = get_file_info(submission.file_path)
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>File Preview - {submission.student_name}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .file-info {{ background: #f8f9fa; padding: 10px; border-radius: 5px; margin-bottom: 20px; }}
            .preview-content {{ border: 1px solid #ddd; padding: 20px; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h2>File Preview: {os.path.basename(submission.file_path)}</h2>
        <div class="file-info">
            <strong>Student:</strong> {submission.student_name}<br>
            <strong>Assignment:</strong> {submission.assignment.title}<br>
            <strong>Submitted:</strong> {submission.submitted_at.strftime('%Y-%m-%d %H:%M:%S')}<br>
            {f'<strong>File Size:</strong> {file_info["size"]}<br>' if file_info else ''}
        </div>
        <div class="preview-content">
            {preview_html}
        </div>
    </body>
    </html>
    """

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
            
            # Send feedback notification if email is available
            if EMAIL_AVAILABLE and submission.student_email:
                try:
                    send_feedback_notification(
                        submission.student_email, 
                        submission.student_name, 
                        submission.assignment.title, 
                        grade, 
                        feedback
                    )
                except Exception as e:
                    print(f"❌ Email notification failed: {e}")

    assignments = Assignment.query.all()
    submissions = Submission.query.all()
    submission_list = [s.to_dict() for s in submissions]
    # Also pass Submission objects for form rendering
    return render_template(
        "dashboard_complete.html",
        assignments=assignments,
        submissions=submission_list,
        submission_objs=submissions
    )

@app.route("/bulk-grade", methods=["POST"])
def bulk_grade():
    """Handle bulk grading operations"""
    if "teacher_id" not in session:
        return redirect(url_for("login"))
    
    action = request.form.get("action")
    submission_ids = request.form.getlist("submission_ids")
    
    if not submission_ids:
        return redirect(url_for("dashboard"))
    
    submissions = Submission.query.filter(Submission.id.in_(submission_ids)).all()
    
    if action == "grade":
        grade = request.form.get("bulk_grade")
        feedback = request.form.get("bulk_feedback", "")
        
        for submission in submissions:
            submission.grade = grade
            submission.feedback = feedback
            # Send email notification
            if EMAIL_AVAILABLE and submission.student_email:
                try:
                    send_feedback_notification(
                        submission.student_email,
                        submission.student_name,
                        submission.assignment.title,
                        grade,
                        feedback
                    )
                except Exception as e:
                    print(f"❌ Email notification failed: {e}")
    
    elif action == "mark_late":
        for submission in submissions:
            submission.is_late = True
    
    elif action == "mark_plagiarism_review":
        # Add a flag for manual plagiarism review
        for submission in submissions:
            # You could add a field like needs_review = True
            pass
    
    db.session.commit()
    return redirect(url_for("dashboard"))

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
    with app.app_context():
        db.create_all()
        print("✅ Database tables created.")
        print("🎉 COMPLETE APPLICATION STARTED!")
        print("=" * 50)
        print("📊 FEATURES STATUS:")
        print(f"   📧 Email notifications: {'✅ Available' if EMAIL_AVAILABLE else '❌ Not available'}")
        print(f"   🔍 AI detection: {'✅ Available' if AI_DETECTION_AVAILABLE else '❌ Not available'}")
        print(f"   📄 File preview: {'✅ Available' if FILE_PREVIEW_AVAILABLE else '❌ Not available'}")
        print(f"   🔍 Plagiarism detection: {'✅ Available' if PLAGIARISM_AVAILABLE else '❌ Not available'}")
        print(f"   📊 PDF reports: {'✅ Available' if REPORTLAB_AVAILABLE else '❌ Not available'}")
        print("=" * 50)
        print("🚀 Access your application at: http://localhost:5000")
        print("👨‍🏫 Teacher login: admin@teacher.com / admin123")
        print("=" * 50)
    app.run(debug=True)
