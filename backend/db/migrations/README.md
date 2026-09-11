# Database migrations

Run migrations in their numeric order using the Supabase SQL editor.

`003_government_official_signups.sql` creates the verification-application
records used by `POST /api/v1/auth/signup`.

`001_alert_lifecycle.sql` prepares alert storage for a temporary mock source now
and an ML source later. It does not create or require a predictions table.

## Lifecycle

`PREDICTED` → `CREATED` → `PENDING` → `SENT` → `ACKNOWLEDGED` or `EXPIRED`

`FAILED` is available when a notification provider rejects or cannot deliver an
alert. `CREATED`, `PENDING`, and `SENT` are considered active for duplicate
prevention. A later alert at a higher severity is allowed.
