-- Alert lifecycle foundation. This deliberately does not depend on ML output.
-- `source` can be MOCK today and ML when the model integration is finalized.

ALTER TABLE public.alerts
    ADD COLUMN IF NOT EXISTS source varchar(30) NOT NULL DEFAULT 'MOCK',
    ADD COLUMN IF NOT EXISTS source_reference varchar(100),
    ADD COLUMN IF NOT EXISTS dedupe_key varchar(160),
    ADD COLUMN IF NOT EXISTS expires_at timestamptz,
    ADD COLUMN IF NOT EXISTS acknowledged_at timestamptz,
    ADD COLUMN IF NOT EXISTS acknowledged_by varchar(100),
    ADD COLUMN IF NOT EXISTS notification_channel varchar(30),
    ADD COLUMN IF NOT EXISTS delivery_error text,
    ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();

-- Covers the lifecycle agreed for dashboard and notification workflows.
ALTER TABLE public.alerts
    DROP CONSTRAINT IF EXISTS alerts_status_check;

ALTER TABLE public.alerts
    ADD CONSTRAINT alerts_status_check CHECK (
        status IN (
            'PREDICTED', 'CREATED', 'PENDING', 'SENT',
            'ACKNOWLEDGED', 'EXPIRED', 'FAILED'
        )
    );

ALTER TABLE public.alerts
    DROP CONSTRAINT IF EXISTS alerts_alert_level_check;

ALTER TABLE public.alerts
    ADD CONSTRAINT alerts_alert_level_check CHECK (
        alert_level IN ('LOW', 'MODERATE', 'HIGH', 'VERY_HIGH', 'SEVERE')
    );

-- One active alert per ward, severity, and source. This is the concurrency-safe
-- database guard against repeated hourly alerts for the same condition.
CREATE UNIQUE INDEX IF NOT EXISTS alerts_one_active_per_condition
    ON public.alerts (ward_id, alert_level, source)
    WHERE status IN ('CREATED', 'PENDING', 'SENT');

CREATE INDEX IF NOT EXISTS alerts_active_lookup_idx
    ON public.alerts (status, created_at DESC);

CREATE INDEX IF NOT EXISTS alerts_ward_history_idx
    ON public.alerts (ward_id, created_at DESC);
