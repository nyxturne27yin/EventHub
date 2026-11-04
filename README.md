EventHub
Centralized University Event Management Platform
EventHub is a web application project to bring university event announcements and registrations into one place. Students can discover events and manage their registrations, organizers can publish and manage events, and administrators can oversee users and access.

Project Goals
Centralize university event information.
Help students browse, search, filter, and view event details.
Support event registration with deadline, capacity, and duplicate-registration checks.
Let authorized organizers manage events and participants.
Provide role-based access for students, organizers, and administrators.
Support registration confirmations, event updates, and registered-event tracking.
Planned Features
The requirements report describes the intended product scope. These features are planned; check the project board for implementation progress.

Core platform
Account registration and login
Student, Organizer, and Administrator roles
Event creation, editing, cancellation, discovery, search, and filtering
Event registration and cancellation
Registration deadline, capacity, and duplicate-registration checks
Notifications, registration confirmations, and event tracking
Administrative user and permission management
Certificate backlog
The supplied Jira snapshot lists these certificate stories as To Do. The requirements report describes digital certificates and QR-based verification as future enhancements beyond the core scope.

Generate digital certificates with unique IDs and QR codes
Add a certificate folder to student profiles
Organize certificates into Academic and Research categories
Verify certificates
User Roles
Student — discovers events and manages event registrations.
Organizer — publishes and manages events and participants.
Administrator — oversees users, access, and platform activity.
Technology Plan
Area	Planned technology
Backend	Python, FastAPI
Frontend	HTML5, CSS3, JavaScript, Bootstrap
Database	PostgreSQL
Database access	SQLAlchemy ORM
Authentication and authorization	JWT, password hashing, role-based access control
Deployment target	Render
Version control	Git and GitHub
Proposed Architecture
The requirements report proposes a layered client-server web application. The team will confirm and develop the architecture under EV-7.

Presentation: Browser interface for students, organizers, and administrators.
Application and business logic: FastAPI endpoints, validation, authentication, and event workflows.
Data access: SQLAlchemy sessions, queries, and relationships.
Database: PostgreSQL storage for users, events, registrations, categories, and notifications.
Security: JWT authentication, password hashing, and role-based authorization.
Current Repository Structure
EventHub/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   └── main.py
│   ├── README.md
│   └── requirements.txt
├── frontend/
│   └── README.md
├── .gitignore
└── README.md
Current implemented features
Organizer event cover images (JPG, PNG, WebP; maximum 5 MB) with server-side content validation and local file storage.
Event cover images displayed in discovery cards, student registration cards, organizer event cards, and event details.
Organizer-only event editing and cover image replacement/removal.
Password reset links using hashed, expiring, single-use tokens.
A persisted 60-second per-account reset cooldown and a lightweight process-local per-IP request guard. For multi-worker production deployments, add a shared Redis or reverse-proxy rate limiter.
Development-only reset-link logging when SMTP is not configured or delivery fails. Never enable development mode in production.
Running the Project
From the repository root, run these commands in PowerShell:

py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt

# Configure .env with DB_PASSWORD and the other database values.
# For local development only, set APP_ENV=development.

Set-Location backend
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
In a second PowerShell terminal, serve the frontend:

Set-Location frontend
python -m http.server 5500
Open http://127.0.0.1:5500. The API origin is centralized in frontend/js/config.js; change window.EVENTHUB_API_BASE_URL there for a deployed backend, and configure CORS_ORIGINS on the backend to allow the frontend origin. For password-reset emails, configure SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL, and FRONTEND_BASE_URL in .env. In development mode, if SMTP is unavailable, the backend terminal logs a development-only reset link. Reset tokens are never returned by the public API.

Event cover images are stored under backend/uploads/event-covers/ by default; the directory is excluded from Git so uploaded user content is not committed. Set EVENT_UPLOAD_DIR to a persistent mounted directory for deployments (for example, /var/data/eventhub-uploads on a configured persistent disk). The Alembic migrations add the nullable events.cover_image_url and password-reset cooldown column without deleting existing records.

The health check is available at http://127.0.0.1:8000/health. Interactive API documentation is available at /docs and /redoc while the server is running.

Team
Member	Project role
Nowrin Akhter Riya	Project Manager
Tashnin Khan Tanisha	Lead
Fahmida Tabassum	QA Lead
Afzalun Nesa Adita	Reporting Lead