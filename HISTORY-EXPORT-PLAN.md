# Upload history and CSV export plan

## 1. Save upload history
- Store each successful upload in SQLite: ID, UTC upload time, filename, extracted document/records, and validation results as a snapshot. Do not store the original XML.
- Use a Docker named volume for the database so history survives container restarts and rebuilds. Failed uploads must not create history entries.
- Keep the existing upload response compatible; include the new upload ID. Add endpoints to list uploads (newest first) and retrieve a snapshot by ID; return 404 for unknown IDs.
- Add a compact history list with filename, time, and issue counts. Selecting an entry reopens its saved results without rerunning validators; show loading, empty, and error states.

## 2. Export validation results
- Add an **Export CSV** action for the currently displayed upload, including reopened history entries.
- Export **all findings**, regardless of the current UI filter; label this scope clearly. Include severity, address code, message, and issue type; include headers even when there are no findings.
- Use proper CSV quoting and UTF-8, neutralize spreadsheet formula injection in user-controlled cells, and return a safe download filename.

## 3. Verify
- Test successful and failed uploads, list/detail APIs, missing IDs, saved snapshot fidelity, and persistence after container restart.
- Test CSV headers, filtering-independent scope, empty findings, special characters, and formula-like values.
- Run backend tests and the frontend build in Docker; manually check upload → history → reopen → export with `docker compose up`.

Implementation order: persistence and API → history UI → export → integration checks. No extra framework or styling work is planned.
