# EV-122: Performance Test Results

## Recorded measurements
| Area | Requests / runs | Average | Minimum | Maximum | Result |
|---|---:|---:|---:|---:|---|
| GET /events/ | 10 | 7.49 ms | 3.56 ms | 26.59 ms | HTTP response received; empty event list |
| GET /events/?search=event | 10 | 11.69 ms | 5.83 ms | 60.43 ms | HTTP response received; no matching events |
| GET /registrations/me | 10 | 16.64 ms | 14.10 ms | 22.20 ms | HTTP 200 on all 10 requests |
| Student Dashboard navigation | 1 recorded measurement | 102.10 ms | — | — | Browser navigation loadEventEnd |

## Notes
- API response times are based on the previously recorded 10-run measurements.
- The Dashboard value is the browser navigation loadEventEnd measurement; it is not a measurement of complete visual rendering.
- The event list and search returned no event records during measurement.
- No approved performance threshold was provided, so pass/fail status is not assigned.
- These are previously recorded results; no new performance test was run for this report.
