from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import os

# Create a simple Flask app for seeding
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy()

# Define the Teacher model
class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

# Initialize db with app
db.init_app(app)

with app.app_context():
    # Create all tables
    db.create_all()
    
    # Clear existing teachers (optional)
    Teacher.query.delete()

    # Create a test teacher
    teacher = Teacher(
        name="Admin Teacher",
        email="admin@teacher.com",
        password=generate_password_hash("admin123")
    )

    db.session.add(teacher)
    db.session.commit()

    print("✅ Database created and seeded successfully!")
    print("✅ Teacher account: admin@teacher.com / admin123")
