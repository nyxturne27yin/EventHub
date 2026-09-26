# EventHub

### Centralized University Event Management Platform

EventHub is a web application project to bring university event announcements and registrations into one place. Students can discover events and manage their registrations, organizers can publish and manage events, and administrators can oversee users and access.

## Project Goals

- Centralize university event information.
- Help students browse, search, filter, and view event details.
- Support event registration with deadline, capacity, and duplicate-registration checks.
- Let authorized organizers manage events and participants.
- Provide role-based access for students, organizers, and administrators.
- Support registration confirmations, event updates, and registered-event tracking.

## Planned Features

The requirements report describes the intended product scope. These features are planned; check the project board for implementation progress.

### Core platform

- Account registration and login
- Student, Organizer, and Administrator roles
- Event creation, editing, cancellation, discovery, search, and filtering
- Event registration and cancellation
- Registration deadline, capacity, and duplicate-registration checks
- Notifications, registration confirmations, and event tracking
- Administrative user and permission management

### Certificate backlog

The supplied Jira snapshot lists these certificate stories as To Do. The requirements report describes digital certificates and QR-based verification as future enhancements beyond the core scope.

- Generate digital certificates with unique IDs and QR codes
- Add a certificate folder to student profiles
- Organize certificates into Academic and Research categories
- Verify certificates

## User Roles

- **Student** — discovers events and manages event registrations.
- **Organizer** — publishes and manages events and participants.
- **Administrator** — oversees users, access, and platform activity.

## Technology Plan

| Area | Planned technology |
|---|---|
| Backend | Python, FastAPI |
| Frontend | HTML5, CSS3, JavaScript, Bootstrap |
| Database | PostgreSQL |
| Database access | SQLAlchemy ORM |
| Authentication and authorization | JWT, password hashing, role-based access control |
| Deployment target | Render |
| Version control | Git and GitHub |

## Proposed Architecture

The requirements report proposes a layered client-server web application. The team will confirm and develop the architecture under EV-7.

1. **Presentation:** Browser interface for students, organizers, and administrators.
2. **Application and business logic:** FastAPI endpoints, validation, authentication, and event workflows.
3. **Data access:** SQLAlchemy sessions, queries, and relationships.
4. **Database:** PostgreSQL storage for users, events, registrations, categories, and notifications.
5. **Security:** JWT authentication, password hashing, and role-based authorization.


## Current Repository Structure

```text
EventHub/
├── backend/
│   └── README.md
├── frontend/
│   └── README.md
├── .gitignore
└── README.md
```

The FastAPI application entry point, dependency manifest, and run instructions will be added during backend setup.

## Team

| Member | Project role |
|---|---|
| Nowrin Akhter Riya | Project Manager |
| Tashnin Khan Tanisha | Lead |
| Fahmida Tabassum | QA Lead |
| Afzalun Nesa Adita | Reporting Lead |