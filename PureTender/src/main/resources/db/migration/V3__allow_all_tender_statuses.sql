ALTER TABLE tenders
    DROP CONSTRAINT IF EXISTS tenders_status_check;

ALTER TABLE tenders
    ADD CONSTRAINT tenders_status_check
    CHECK (status IN (
        'SUBMITTED',
        'PUBLISHED',
        'REJECTED',
        'UNDER_EVALUATION',
        'ON_HOLD',
        'AWARDED',
        'CANCELLED',
        'VOIDED'
    ));
