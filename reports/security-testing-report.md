# EventHub Security Testing Report

## 1. Overview
- Project: UAP EventHub
- Task: EV-124 Security Testing
- Testing environment: Local development
- Test framework: Pytest, FastAPI TestClient
- Database: Focused authentication tests use mocked/fake dependencies; the complete suite uses the existing project test setup.
- Scope: Authentication, JWT validation, authorization, input validation, ownership checks, and sensitive data exposure.

## 2. Test Execution

| Test | Result |
|---|---|
| Existing JWT authentication tests | Passed |
| New wrong-signature JWT test | Passed |
| New missing-subject JWT test | Passed |
| Existing RBAC tests | Passed |
| Complete backend test suite | 188 passed |
| Total warnings | 7 deprecation warnings |

Command:
`pytest backend/tests -q`

Result: 188 passed, 7 warnings.

## 3. Security Controls Reviewed

- Passwords are hashed using pwdlib PasswordHash.
- Login returns a generic invalid-credentials response.
- JWT expiration is added when creating access tokens.
- JWT decoding validates the configured signing algorithm and signature.
- Missing and malformed user subjects are rejected.
- Inactive users cannot access protected endpoints.
- Role-based authorization checks the current user's role.
- Registration records use the authenticated student's ID.
- Students can cancel only their own registrations.
- Organizers can manage participants only for their own events.
- Registration status accepts only Registered or Cancelled.
- Registration schemas reject unexpected fields.
- Frontend searches found no innerHTML, insertAdjacentHTML, outerHTML, document.write, or eval usage in the inspected JS/HTML files.

## 4. Findings and Recommendations

### SEC-01: Default JWT signing secret
Severity: High if deployed without an environment-provided secret.

The application configuration contains a hardcoded fallback JWT secret. If deployment does not provide a strong, unique JWT_SECRET_KEY, token signing may rely on a predictable development value.

Recommendation:
Require a strong secret from the deployment environment and fail securely when it is missing. Never commit actual secrets.

Status: Configuration risk identified; deployment configuration not verified.

### SEC-02: Organizer profile information visibility
Severity: Review required.

Authenticated users can retrieve another organizer's profile, including contact_phone, bio, and organization details.

Recommendation:
Confirm which profile fields are intended to be public and restrict private fields if necessary.

Status: Requires product/privacy policy confirmation.

### SEC-03: Public certificate verification data
Severity: Review required.

Public certificate verification returns the student's name, event title, certificate category, and issue date.

Recommendation:
Confirm that certificate holders are informed of this public disclosure and that the returned fields are necessary.

Status: Requires privacy policy confirmation.

### SEC-04: Password reset timestamp deprecation
Severity: Low / maintenance.

The password reset implementation and tests use datetime.utcnow(), which produces deprecation warnings.

Recommendation:
Migrate to timezone-aware UTC timestamps consistently.

Status: Non-blocking maintenance issue.

## 5. Limitations

- No production environment was tested.
- No real user data was accessed.
- Endpoint-level IDOR tests for every ownership-sensitive route remain outstanding.
- Deployment secret configuration was not verified.
- Frontend inspection was a static search, not a complete dynamic XSS assessment.
- Privacy expectations for organizer profiles and certificate verification require confirmation.

## 6. Conclusion

The existing backend test suite and additional JWT security tests passed.

The review identified a JWT configuration risk and two data-visibility areas requiring policy confirmation. Further endpoint-level authorization and privacy testing is recommended before production deployment.

No production application code was modified as part of this test-only change.
