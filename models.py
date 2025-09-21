# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)  # hashed password
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
