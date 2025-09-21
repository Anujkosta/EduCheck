# 📚 Academic Assignment Management System

A comprehensive Flask-based web application for managing academic assignments with advanced plagiarism detection, AI content detection, and email notifications.

## ✨ Features

### 🔐 **Authentication & Security**
- Secure teacher and student authentication with password hashing
- Session management and access control
- File upload validation and security measures
- Environment-based configuration

### 📝 **Assignment Management**
- Create and manage assignments with due dates
- Support for multiple file formats (PDF, DOCX, TXT, images)
- Real-time submission tracking
- Late submission detection and alerts

### 🔍 **Advanced Detection Systems**
- **Plagiarism Detection**: Text similarity, image comparison, document analysis
- **AI Content Detection**: Multi-heuristic approach to identify AI-generated content
- Detailed plagiarism reports with highlighted content
- Configurable detection thresholds

### 📧 **Email Notifications**
- Assignment deadline reminders
- Feedback notifications
- Late submission alerts
- Plagiarism detection alerts

### 📊 **Analytics & Reporting**
- Comprehensive dashboard with visual charts
- Submission statistics and trends
- Plagiarism and AI detection analytics
- Export capabilities

### 🔧 **Additional Features**
- File preview functionality
- Bulk grading operations
- REST API for mobile integration
- Dark mode support
- Responsive design

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip (Python package installer)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd assignment-management-system
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   python seed.py
   ```

6. **Run the application**
   ```bash
   python app.py
   ```

7. **Access the application**
   - Open your browser and go to `http://localhost:5000`
   - Default teacher login: `admin@teacher.com` / `admin123`

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
FLASK_DEBUG=True

# Database Configuration
DATABASE_URL=sqlite:///app.db

# Email Configuration (Optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@assignmentmanager.com

# File Upload Configuration
MAX_FILE_SIZE=16777216  # 16MB in bytes
UPLOAD_FOLDER=uploads

# Plagiarism Detection
PLAGIARISM_THRESHOLD=50
AI_DETECTION_THRESHOLD=65
```

### Email Setup (Optional)

To enable email notifications:

1. **Gmail Setup**:
   - Enable 2-factor authentication
   - Generate an app password
   - Use the app password in `MAIL_PASSWORD`

2. **Other SMTP Providers**:
   - Update `MAIL_SERVER`, `MAIL_PORT`, and `MAIL_USE_TLS` accordingly

## 📱 API Endpoints

The application includes a REST API for mobile app integration:

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout

### Assignments
- `GET /api/assignments` - Get all assignments
- `GET /api/assignments/<id>` - Get specific assignment

### Submissions
- `GET /api/submissions` - Get all submissions (teachers)
- `POST /api/submissions` - Create submission (students)
- `PUT /api/submissions/<id>/grade` - Grade submission (teachers)

### Analytics
- `GET /api/analytics/overview` - Get analytics overview

## 🏗️ Project Structure

```
assignment-management-system/
├── app.py                 # Main Flask application
├── models.py              # Database models
├── config.py              # Configuration settings
├── api.py                 # REST API endpoints
├── seed.py                # Database seeding
├── requirements.txt       # Python dependencies
├── env.example           # Environment variables template
├── README.md             # This file
├── static/
│   └── modern.css        # Custom styles
├── templates/            # HTML templates
├── utils/                # Utility modules
│   ├── ai_detection.py   # AI content detection
│   ├── email_service.py  # Email notifications
│   └── file_preview.py   # File preview functionality
├── plagiarism/           # Plagiarism detection
│   └── plagiarism_checker.py
├── uploads/              # Uploaded files
├── reports/              # Generated reports
└── instance/             # Database files
```

## 🔧 Development

### Running in Development Mode
```bash
export FLASK_ENV=development
export FLASK_DEBUG=True
python app.py
```

### Database Migrations
```bash
# Create migration
flask db migrate -m "Description"

# Apply migration
flask db upgrade
```

### Testing
```bash
# Run tests (when implemented)
python -m pytest tests/
```

## 🚀 Deployment

### Production Deployment

1. **Set production environment variables**
2. **Use a production WSGI server** (e.g., Gunicorn)
3. **Set up a reverse proxy** (e.g., Nginx)
4. **Use a production database** (e.g., PostgreSQL)
5. **Enable HTTPS**

### Docker Deployment (Optional)

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the code comments

## 🔄 Recent Updates

### Version 2.0 (Current)
- ✅ Enhanced security with password hashing
- ✅ Improved AI detection algorithms
- ✅ Email notification system
- ✅ File preview functionality
- ✅ Bulk operations for teachers
- ✅ REST API endpoints
- ✅ Better error handling
- ✅ Environment-based configuration

### Version 1.0
- Basic assignment management
- Simple plagiarism detection
- File upload support
- Basic analytics dashboard

---

**Made with ❤️ for educational institutions**
