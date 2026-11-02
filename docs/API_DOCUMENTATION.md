# EventHub API Documentation

**Version:** 0.1.0

API for university event management.

## Overview

- Total paths: 29
- Total operations: 33
- Interactive API documentation: `/docs`
- OpenAPI specification: `docs/openapi.json`

## Authentication

Protected endpoints require a valid access token. Use the `Authorize` option in Swagger UI and provide the bearer token when required.

Public endpoints do not require authentication. Role restrictions are described in the endpoint implementation and OpenAPI security metadata where available.

## Role-Based Access

| Role | Protected API areas |
|---|---|
| Student | Own registrations, registration cancellation, notifications, and own certificates |
| Organizer | Event creation and management, participant management, certificate generation, and own organizer profile |
| Administrator | Admin dashboard, user management, and event administration |
| Authenticated user | Organizer profile lookup by user ID |
| Public | Health check, registration, login, password reset, event listing/details, and certificate verification |

Actual access is enforced by the backend. The OpenAPI security scheme identifies token-protected operations; consult the endpoint implementation for role-specific restrictions.

## API Endpoints

| Method | Endpoint | Tag | Authentication | Success response |
|---|---|---|---|---|
| GET | `/health` | health | Public | 200 |
| POST | `/auth/register` | Authentication | Public | 201 |
| POST | `/auth/login` | Authentication | Public | 200 |
| POST | `/auth/forgot-password` | Authentication | Public | 200 |
| POST | `/auth/reset-password` | Authentication | Public | 200 |
| GET | `/auth/me` | Authentication | Bearer token | 200 |
| PUT | `/auth/me` | Authentication | Bearer token | 200 |
| POST | `/events/` | Events | Bearer token | 201 |
| GET | `/events/` | Events | Public | 200 |
| GET | `/events/{event_id}` | Events | Public | 200 |
| PATCH | `/events/{event_id}` | Events | Bearer token | 200 |
| POST | `/events/{event_id}/publish` | Events | Bearer token | 200 |
| POST | `/events/{event_id}/cancel` | Events | Bearer token | 200 |
| GET | `/admin/dashboard` | Administration | Bearer token | 200 |
| GET | `/admin/users` | Administration | Bearer token | 200 |
| PATCH | `/admin/users/{user_id}` | Administration | Bearer token | 200 |
| GET | `/admin/events` | Administration | Bearer token | 200 |
| PATCH | `/admin/events/{event_id}/status` | Administration | Bearer token | 200 |
| GET | `/organizer-profiles/me` | Organizer Profiles | Bearer token | 200 |
| PUT | `/organizer-profiles/me` | Organizer Profiles | Bearer token | 200 |
| GET | `/organizer-profiles/{user_id}` | Organizer Profiles | Bearer token | 200 |
| POST | `/certificates/events/{event_id}/generate` | Certificates | Bearer token | 201 |
| GET | `/certificates/me` | Certificates | Bearer token | 200 |
| GET | `/certificates/verify/{certificate_id}` | Certificates | Public | 200 |
| GET | `/certificates/verify/{certificate_id}/qr` | Certificates | Public | 200 |
| GET | `/registrations/me` | Event Registrations | Bearer token | 200 |
| GET | `/registrations/me/upcoming` | Event Registrations | Bearer token | 200 |
| POST | `/events/{event_id}/registrations` | Event Registrations | Bearer token | 201 |
| POST | `/events/{event_id}/registrations/{registration_id}/cancel` | Event Registrations | Bearer token | 200 |
| GET | `/events/{event_id}/participants` | Event Registrations | Bearer token | 200 |
| PATCH | `/events/{event_id}/registrations/{registration_id}/status` | Event Registrations | Bearer token | 200 |
| GET | `/notifications` | Notifications | Bearer token | 200 |
| PATCH | `/notifications/{notification_id}/read` | Notifications | Bearer token | 200 |

## Request and Response Schemas

The complete request and response definitions, field types, required fields, validation rules, and response structures are available in `openapi.json`.

## Common HTTP Status Codes

| Code | Meaning |
|---|---|
| 200 | Request successful |
| 201 | Resource created |
| 400 | Invalid request or validation rule failed |
| 401 | Authentication required or invalid credentials |
| 403 | Insufficient permission |
| 404 | Resource not found |
| 409 | Conflict with current resource state |
| 422 | Request validation failed |
| 500 | Internal server error |

Actual status codes depend on each endpoint. Refer to the OpenAPI specification for endpoint-specific responses.

## How to Use

1. Start the FastAPI backend using the project's configured run command.
2. Open `/docs` in the browser for interactive Swagger documentation.
3. Use the login endpoint to obtain an access token.
4. Click `Authorize` and enter the token if an endpoint requires authentication.
5. Select an endpoint, provide the required parameters or request body, and execute it.

## Source of Documentation

This documentation is generated from the FastAPI application's OpenAPI schema. Regenerate `docs/openapi.json` after API changes to keep the documented paths and schemas synchronized with the implementation.
