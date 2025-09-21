from app_minimal import db, Teacher, app

with app.app_context():
    # Clear existing teachers (optional)
    Teacher.query.delete()

    # Create a test teacher
    from werkzeug.security import generate_password_hash
    teacher = Teacher(
        name="Admin Teacher",
        email="admin@teacher.com",
        password=generate_password_hash("admin123")
    )

    db.session.add(teacher)
    db.session.commit()

    print("✅ Seeded teacher: admin@teacher.com / admin123")
