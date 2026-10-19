-- CEPIO Fabric Live Binding Proof v0.1
-- Run this once in a dedicated Microsoft Fabric Warehouse query editor.
-- The live CEPIO identity should subsequently receive SELECT only on this proof schema.

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'cepio_proof')
    EXEC('CREATE SCHEMA [cepio_proof]');

IF OBJECT_ID('[cepio_proof].[cepio_drilling_npt_context]', 'U') IS NULL
BEGIN
    CREATE TABLE [cepio_proof].[cepio_drilling_npt_context] (
        context_id VARCHAR(100) NOT NULL,
        source_record_id VARCHAR(100) NOT NULL,
        source_record_version VARCHAR(100) NOT NULL,
        rig_id VARCHAR(100) NOT NULL,
        rig_name VARCHAR(200) NOT NULL,
        rig_source_record_id VARCHAR(100) NOT NULL,
        rig_source_record_version VARCHAR(100) NOT NULL,
        well_id VARCHAR(100) NOT NULL,
        well_name VARCHAR(200) NOT NULL,
        well_source_record_id VARCHAR(100) NOT NULL,
        well_source_record_version VARCHAR(100) NOT NULL
    );
END;

IF OBJECT_ID('[cepio_proof].[cepio_drilling_activity_interval]', 'U') IS NULL
BEGIN
    CREATE TABLE [cepio_proof].[cepio_drilling_activity_interval] (
        context_id VARCHAR(100) NOT NULL,
        activity_id VARCHAR(100) NOT NULL,
        activity_name VARCHAR(200) NOT NULL,
        start_time VARCHAR(64) NOT NULL,
        end_time VARCHAR(64) NOT NULL,
        source_record_id VARCHAR(100) NOT NULL,
        source_record_version VARCHAR(100) NOT NULL
    );
END;

IF OBJECT_ID('[cepio_proof].[cepio_drilling_activity_classification]', 'U') IS NULL
BEGIN
    CREATE TABLE [cepio_proof].[cepio_drilling_activity_classification] (
        context_id VARCHAR(100) NOT NULL,
        activity_id VARCHAR(100) NOT NULL,
        classification_id VARCHAR(100) NOT NULL,
        classification_name VARCHAR(200) NOT NULL,
        is_productive BIT NOT NULL,
        source_record_id VARCHAR(100) NOT NULL,
        source_record_version VARCHAR(100) NOT NULL
    );
END;

DELETE FROM [cepio_proof].[cepio_drilling_activity_classification]
WHERE context_id = 'NPT-CONTEXT-001';
DELETE FROM [cepio_proof].[cepio_drilling_activity_interval]
WHERE context_id = 'NPT-CONTEXT-001';
DELETE FROM [cepio_proof].[cepio_drilling_npt_context]
WHERE context_id = 'NPT-CONTEXT-001';

INSERT INTO [cepio_proof].[cepio_drilling_npt_context] (
    context_id, source_record_id, source_record_version,
    rig_id, rig_name, rig_source_record_id, rig_source_record_version,
    well_id, well_name, well_source_record_id, well_source_record_version
)
VALUES (
    'NPT-CONTEXT-001', 'NPT-CONTEXT-001', '7',
    'RIG-1', 'Rig 1', 'FAB-RIG-1', '14',
    'WELL-1', 'Well 1', 'FAB-WELL-1', '9'
);

INSERT INTO [cepio_proof].[cepio_drilling_activity_interval] (
    context_id, activity_id, activity_name, start_time, end_time,
    source_record_id, source_record_version
)
VALUES
(
    'NPT-CONTEXT-001', 'ACT-NPT', 'Top drive downtime',
    '2026-10-18T10:00:00+03:00', '2026-10-18T12:00:00+03:00',
    'FAB-ACT-NPT', '21'
),
(
    'NPT-CONTEXT-001', 'ACT-PROD', 'Drilling ahead',
    '2026-10-18T12:00:00+03:00', '2026-10-18T13:30:00+03:00',
    'FAB-ACT-PROD', '22'
);

INSERT INTO [cepio_proof].[cepio_drilling_activity_classification] (
    context_id, activity_id, classification_id, classification_name,
    is_productive, source_record_id, source_record_version
)
VALUES
(
    'NPT-CONTEXT-001', 'ACT-NPT', 'CLASS-NPT', 'Non-productive',
    0, 'FAB-CLASS-NPT', '31'
),
(
    'NPT-CONTEXT-001', 'ACT-PROD', 'CLASS-PROD', 'Productive',
    1, 'FAB-CLASS-PROD', '32'
);

SELECT 'CEPIO Fabric proof dataset ready' AS status, 'NPT-CONTEXT-001' AS context_id;
