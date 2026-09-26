# EventHub

## Project Overview

EventHub is a university software engineering project to build a centralized platform for discovering and managing university events.

## Project Status

Sprint 1 is in progress. The project structure and Git workflow are being established. Application features are planned and are not yet implemented.

## Planned User Roles

Student, Organizer, and Admin.

## Planned Features

User accounts and role-based access; event creation and discovery; event registration; capacity and deadline handling; notifications; and administration tools.

## Planned Technology Stack

Python, FastAPI, PostgreSQL, SQLAlchemy, HTML, CSS, JavaScript, and Bootstrap.

## Project Structure

- `backend/` — backend code; setup begins in EV-3.
- `frontend/` — user interface files.
- `.gitignore` — excludes local environments, generated files, and secrets.

## Environment Setup

Create a local Python virtual environment from the repository root with `py -m venv .venv`. In PowerShell, activate it with `.\.venv\Scripts\Activate.ps1`. Do not commit `.venv`. A dependency list will be added when backend dependencies are established.

## Configuration and Secrets

Keep local credentials in an untracked `.env` file. Never commit passwords, database credentials, or signing keys. A safe `.env.example` template can be added when configuration is introduced.

## Running the Project

The application is not runnable yet. FastAPI setup and run instructions will be added in EV-3.

## API Documentation and Database

FastAPI documentation is planned after the API is implemented. PostgreSQL setup is EV-5; SQLAlchemy ORM work is assigned to EV-6.

## Testing

Testing setup will be documented when the backend is established.

## Git Workflow

Develop each Jira task on its own feature branch and submit a pull request to `main`. Include the Jira ID in branch names, commit messages, and pull request titles or descriptions.

Example branch: `feature/EV-2-project-structure`

## Team

- Tanisha — EV-2 project structure, EV-3 FastAPI backend, EV-5 PostgreSQL setup
- Adita — EV-4 frontend, EV-17 user registration form
- Riya — EV-6 SQLAlchemy ORM, EV-7 modular system architecture
- Fahmida — EV-18 registration API, EV-19 user information validation