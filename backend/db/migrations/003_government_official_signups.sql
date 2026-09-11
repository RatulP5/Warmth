-- Initial, intentionally small registration record for government officials.
-- Uploaded documents remain on the application server; only their metadata is
-- kept in PostgreSQL so a future storage provider can be introduced cleanly.
CREATE TABLE IF NOT EXISTS public.government_official_signups (
    signup_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    official_email varchar(254) NOT NULL,
    mobile_number varchar(20) NOT NULL,
    employee_id varchar(100) NOT NULL,
    designation varchar(150) NOT NULL,
    ministry_department varchar(200) NOT NULL,
    organization_level varchar(100) NOT NULL,
    verification_document_path text NOT NULL,
    verification_document_name varchar(255) NOT NULL,
    verification_document_mime_type varchar(100) NOT NULL,
    -- These fields support the demo official dashboard login and ward-based
    -- alert matching described in GOVERNMENT_OFFICIAL_ALERT_ARCHITECTURE.md.
    ward_name varchar(100) NOT NULL,
    password_hash text NOT NULL,
    notification_mode varchar(20) NOT NULL DEFAULT 'SIMULATED',
    -- This demo only registers pre-approved government officials.
    verification_status varchar(20) NOT NULL DEFAULT 'APPROVED',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT government_official_signups_email_key UNIQUE (official_email),
    CONSTRAINT government_official_signups_employee_id_key UNIQUE (employee_id),
    CONSTRAINT government_official_signups_status_check
        CHECK (verification_status IN ('PENDING', 'APPROVED', 'REJECTED')),
    CONSTRAINT government_official_signups_notification_mode_check
        CHECK (notification_mode IN ('SIMULATED', 'EMAIL', 'SMS'))
);
