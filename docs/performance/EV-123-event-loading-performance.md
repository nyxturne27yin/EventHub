# EV-123: Event Loading Performance Test Report

## Objective
Measure event loading and registration-related API response times.

## Results

| Scenario | Average Response Time | Records |
|---|---:|---:|
| Upcoming Events | 1507 ms | 1000 |
| Event Search | 1458 ms | 1000 |
| Event Details | 5.8 ms | 1 |
| Registration Availability | 17.2 ms | 1 |
| Student Registered Events | 62.2 ms | 200 |
| Student Upcoming Events | 47.4 ms | 100 |
| Completed Event History | Not measured separately | Included in registered events |

## Method
Five measurements were collected for repeated scenarios using PowerShell Stopwatch and the browser Performance API. Tests were performed against the local EventHub backend.

## Findings
Event details and registration endpoints responded quickly. Event listing and search took approximately 1.5 seconds with 1,000 returned records. Query optimization and pagination are recommended for further improvement.

## Limitations
- No approved performance threshold was provided; no formal pass/fail decision is made.
- Results represent local testing, not production or concurrent-user load testing.
- Frontend rendering time was not separately measured.
- Completed history uses the registered-events data; separate rendering time was not measured.
- Synthetic test data was inserted into the existing eventhub database: 1,000 upcoming events, 100 completed events, and 600 registrations. Cleanup has not been performed.

## Conclusion
EV-123 API performance measurements are complete. Event listing and search are the main areas identified for further optimization.
