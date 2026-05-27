-- ============================================================
-- BATCH JOB DEPENDENCY RESOLVER  –  MySQL 8.0+
-- ============================================================
-- Purpose  : Resolve stored-procedure execution order for each
--            UNIT_NBR, respecting all STEP_DEP_ID dependencies,
--            and assign a PARALLEL_LEVEL so that steps at the
--            same level can run concurrently.
--
-- Assumptions:
--   A1. STEP_DEP_ID = 0 means "no dependency" (root node).
--   A2. A step is ready only when ALL declared dependencies
--       have completed (AND semantics, not OR. Meaning to say steps 3 and 4 have to be completed before starting step 5).
--   A3. The dependency graph is a Direct Acyclic Graph (no cycles).
--   A4. Schema:
--         PROG_NAME        (UNIT_NBR, STEP_SEQ_ID, STEP_PROG_NAME)
--         DEPENDENCY_RULES (UNIT_NBR, RULE_ID, STEP_SEQ_ID, STEP_DEP_ID)
--   A5. DELIMITER MySQL command is intentionally avoided — VS Code and most
--       MySQL GUI tools do not support it. The stored procedure
--       uses a single SELECT body so no DELIMITER change is needed.
--
-- Known Gaps / Improvement Areas:
--   G1. Cycle Detection
--       Current behaviour: if two steps accidentally depend on each
--       other (e.g. Step A waits for Step B, and Step B waits for
--       Step A), the query will loop forever until MySQL throws a
--       max-recursion error — which is cryptic and hard to debug.
--       Improvement: track the path travelled so far as a string
--       inside the CTE (e.g. '1->2->3'). If we ever see a step ID
--       that is already in the path string, we know a cycle exists
--       and can throw a clear, human-readable error immediately.
--
--   G2. Cross-Unit Dependencies
--       Current behaviour: each batch job (UNIT_NBR) is treated as
--       completely independent. There is no way to say "Job 2 cannot
--       start until Step 5 of Job 1 has finished."
--       Improvement: add a DEP_UNIT_NBR column to DEPENDENCY_RULES
--       so a step in one job can declare a dependency on a step in
--       a different job, enabling cross-job orchestration.
--
--   G3. Uniform Step Duration Assumed
--       Current behaviour: PARALLEL_LEVEL groups steps into waves
--       (1, 2, 3...) but assumes every step takes the same amount
--       of time. In reality, one step might take 2 seconds and
--       another might take 2 hours, so grouping them together
--       gives a misleading picture of the schedule.
--       Improvement: assign each step an estimated duration and use
--       Critical Path Method (CPM) to calculate the earliest and
--       latest each step can start — giving a more accurate
--       execution timeline.
--
--   G4. No Execution Status Tracking
--       Current behaviour: the solution only plans the order of
--       execution. It has no way to know whether a step has actually
--       started, succeeded, or failed at runtime.
--       Improvement: introduce a JOB_RUN table that records the
--       status of each step in real time (e.g. PENDING, RUNNING,
--       COMPLETED, FAILED). The scheduler would then query this
--       table to decide which steps are ready to fire next, and
--       operators could monitor or retry failed steps.
-- ============================================================


-- ============================================================
-- 0.  SESSION SETTINGS
-- ============================================================

SET SESSION cte_max_recursion_depth = 10000;


-- ============================================================
-- 1.  DDL  –  reference tables
-- ============================================================

DROP TABLE IF EXISTS DEPENDENCY_RULES;
DROP TABLE IF EXISTS PROG_NAME;

CREATE TABLE PROG_NAME (
    UNIT_NBR       INT          NOT NULL,
    STEP_SEQ_ID    INT          NOT NULL,
    STEP_PROG_NAME VARCHAR(200) NOT NULL,
    CONSTRAINT pk_prog_name PRIMARY KEY (UNIT_NBR, STEP_SEQ_ID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE DEPENDENCY_RULES (
    UNIT_NBR    INT NOT NULL,
    RULE_ID     INT NOT NULL,
    STEP_SEQ_ID INT NOT NULL,
    STEP_DEP_ID INT NOT NULL,
    CONSTRAINT pk_dep_rules PRIMARY KEY (UNIT_NBR, RULE_ID),
    INDEX idx_dep_step   (UNIT_NBR, STEP_SEQ_ID),
    INDEX idx_dep_parent (UNIT_NBR, STEP_DEP_ID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ============================================================
-- 2.  INSERT DATA
-- ============================================================

INSERT INTO PROG_NAME (UNIT_NBR, STEP_SEQ_ID, STEP_PROG_NAME) VALUES
    (1,  1, 'PKGIDS_CMMN_UTILITY.PROCIDS_JOB_START'),
    (1,  2, 'pkgids_ptf_hrchy_processing.Procids_delete_job_set_nbr'),
    (1,  3, 'PKGIDS_PTF_EXTR.ext_static_ptf_table'),
    (1,  4, 'PKGIDS_PTF_EXTR.ext_eff_ptf_table'),
    (1,  5, 'pkgids_ptf_hrchy_processing.procids_get_tree_a'),
    (1,  6, 'pkgids_ptf_hrchy_processing.procids_get_tree_b'),
    (1,  7, 'pkgids_ptf_hrchy_processing.procids_get_tree_c'),
    (1,  8, 'pkgids_ptf_hrchy_processing.procids_get_tree_d'),
    (1,  9, 'pkgids_ptf_hrchy_processing.procids_get_tree_e'),
    (1, 10, 'pkgids_ptf_hrchy_processing.procids_get_active_portf'),
    (1, 11, 'pkgids_ptf_lineage.procids_process_ptf_lineage'),
    (1, 12, 'pkgids_ptf_lineage.procids_summary_to_bookable_rs'),
    (1, 13, 'PKGIDS_CMMN_UTILITY.PROCIDS_JOB_END');

INSERT INTO DEPENDENCY_RULES (UNIT_NBR, RULE_ID, STEP_SEQ_ID, STEP_DEP_ID) VALUES
    (1,  1,  1,  0),
    (1,  2,  2,  1),
    (1,  3,  3,  2),
    (1,  4,  4,  2),
    (1,  5,  5,  3),
    (1,  6,  5,  4),
    (1,  7,  6,  3),
    (1,  8,  6,  4),
    (1,  9,  7,  3),
    (1, 10,  7,  4),
    (1, 11,  8,  3),
    (1, 12,  9,  3),
    (1, 13,  8,  4),
    (1, 14,  9,  4),
    (1, 15, 10,  5),
    (1, 16, 10,  6),
    (1, 17, 10,  7),
    (1, 18, 10,  8),
    (1, 19, 10,  9),
    (1, 20, 11, 10),
    (1, 21, 12, 11),
    (1, 22, 13, 12);


-- ============================================================
-- 3.  MAIN QUERY  –  topological level assignment via rCTE
-- ============================================================
--   Step A: Root steps (STEP_DEP_ID = 0) get PARALLEL_LEVEL = 1.
--   Step B: Recursively: child.level = parent.level + 1.
--   Step C: Final level = MAX over all incoming paths
--           (critical-path rule — step waits for slowest parent).
--   Step D: Join PROG_NAME for human-readable output.
-- ============================================================

WITH RECURSIVE
    edges AS (
        SELECT UNIT_NBR,
               STEP_DEP_ID AS parent_step,
               STEP_SEQ_ID AS child_step
        FROM   DEPENDENCY_RULES
        WHERE  STEP_DEP_ID <> 0
    ),
    roots AS (
        SELECT DISTINCT UNIT_NBR,
                        STEP_SEQ_ID AS step_id,
                        1           AS lvl
        FROM   DEPENDENCY_RULES
        WHERE  STEP_DEP_ID = 0
    ),
    traversal AS (
        SELECT unit_nbr, step_id, lvl
        FROM   roots

        UNION ALL

        SELECT e.UNIT_NBR,
               e.child_step AS step_id,
               t.lvl + 1    AS lvl
        FROM   traversal t
        JOIN   edges     e
          ON   e.UNIT_NBR    = t.UNIT_NBR
          AND  e.parent_step = t.step_id
    ),
    final_levels AS (
        SELECT UNIT_NBR,
               step_id,
               MAX(lvl) AS PARALLEL_LEVEL
        FROM   traversal
        GROUP  BY UNIT_NBR, step_id
    )
SELECT
    fl.UNIT_NBR,
    fl.PARALLEL_LEVEL,
    fl.step_id        AS STEP_SEQ_ID,
    p.STEP_PROG_NAME
FROM   final_levels fl
JOIN   PROG_NAME    p
  ON   p.UNIT_NBR    = fl.UNIT_NBR
  AND  p.STEP_SEQ_ID = fl.step_id
ORDER BY
    fl.UNIT_NBR,
    fl.PARALLEL_LEVEL,
    fl.step_id;


-- ============================================================
-- 4.  STORED PROCEDURE
--     No DELIMITER needed — single SELECT body has no internal
--     semicolons, so VS Code and GUI tools handle it fine.
-- ============================================================

DROP PROCEDURE IF EXISTS sp_batch_execution_plan;

CREATE PROCEDURE sp_batch_execution_plan(IN p_unit_nbr INT)
WITH RECURSIVE
    edges AS (
        SELECT UNIT_NBR,
               STEP_DEP_ID AS parent_step,
               STEP_SEQ_ID AS child_step
        FROM   DEPENDENCY_RULES
        WHERE  STEP_DEP_ID <> 0
    ),
    roots AS (
        SELECT DISTINCT UNIT_NBR,
                        STEP_SEQ_ID AS step_id,
                        1           AS lvl
        FROM   DEPENDENCY_RULES
        WHERE  STEP_DEP_ID = 0
    ),
    traversal AS (
        SELECT unit_nbr, step_id, lvl
        FROM   roots

        UNION ALL

        SELECT e.UNIT_NBR,
               e.child_step AS step_id,
               t.lvl + 1    AS lvl
        FROM   traversal t
        JOIN   edges     e
          ON   e.UNIT_NBR    = t.UNIT_NBR
          AND  e.parent_step = t.step_id
    ),
    final_levels AS (
        SELECT UNIT_NBR,
               step_id,
               MAX(lvl) AS PARALLEL_LEVEL
        FROM   traversal
        GROUP  BY UNIT_NBR, step_id
    )
SELECT
    fl.UNIT_NBR,
    fl.PARALLEL_LEVEL,
    fl.step_id        AS STEP_SEQ_ID,
    p.STEP_PROG_NAME
FROM   final_levels fl
JOIN   PROG_NAME    p
  ON   p.UNIT_NBR    = fl.UNIT_NBR
  AND  p.STEP_SEQ_ID = fl.step_id
WHERE  p_unit_nbr IS NULL
    OR fl.UNIT_NBR = p_unit_nbr
ORDER BY
    fl.UNIT_NBR,
    fl.PARALLEL_LEVEL,
    fl.step_id;


-- ============================================================
-- 5.  RUN
-- ============================================================

CALL sp_batch_execution_plan(1);     -- single unit
-- CALL sp_batch_execution_plan(NULL);  -- all units
