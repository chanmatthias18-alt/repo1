-- ============================================================
-- TEST SUITE  –  Batch Job Dependency Resolver  (MySQL 8.0+)
-- ============================================================
-- Run via SQLTools in VS Code:
--   Ctrl+Shift+P -> SQLTools: Run Current File
--
-- Each test loads isolated data, runs the resolver CTE,
-- asserts expected PARALLEL_LEVEL values, and writes
-- PASS/FAIL into a temp results table.
-- ============================================================

SET SESSION cte_max_recursion_depth = 10000;

DROP TEMPORARY TABLE IF EXISTS test_results;
CREATE TEMPORARY TABLE test_results (
    test_name VARCHAR(120),
    status    CHAR(4)
);

-- ============================================================
-- T01  –  Linear chain: 1 → 2 → 3
--         Expected levels: 1=1, 2=2, 3=3
--         Step 1 runs first, then Step 2, then Step 3. Each step runs after one another like a queue. We verify each step gets assigned the correct level (1, 2, 3). If this fails, the entire resolver is broken.
-- ============================================================
INSERT INTO test_results
WITH RECURSIVE
t_dep AS (
    SELECT 99 AS UNIT_NBR, 1 AS RULE_ID, 1 AS STEP_SEQ_ID, 0 AS STEP_DEP_ID
    UNION ALL SELECT 99,2,2,1 UNION ALL SELECT 99,3,3,2
),
edges AS (SELECT UNIT_NBR, STEP_DEP_ID parent_step, STEP_SEQ_ID child_step FROM t_dep WHERE STEP_DEP_ID<>0),
roots AS (SELECT DISTINCT UNIT_NBR, STEP_SEQ_ID step_id, 1 lvl FROM t_dep WHERE STEP_DEP_ID=0),
traversal AS (
    SELECT unit_nbr, step_id, lvl FROM roots
    UNION ALL
    SELECT e.UNIT_NBR, e.child_step, t.lvl+1 FROM traversal t JOIN edges e ON e.UNIT_NBR=t.UNIT_NBR AND e.parent_step=t.step_id
),
final_levels AS (SELECT UNIT_NBR, step_id, MAX(lvl) PARALLEL_LEVEL FROM traversal GROUP BY UNIT_NBR, step_id)
SELECT 'T01 Linear chain 1->2->3',
    IF(
        (SELECT PARALLEL_LEVEL FROM final_levels WHERE step_id=1)=1 AND
        (SELECT PARALLEL_LEVEL FROM final_levels WHERE step_id=2)=2 AND
        (SELECT PARALLEL_LEVEL FROM final_levels WHERE step_id=3)=3,
        'PASS','FAIL');

-- ============================================================
-- T02  –  Two parallel branches: 1→2, 1→3
--         Expected: 1=1, 2=2, 3=2
--         Step 1 runs first, then Steps 2 and 3 can both run at the same time because they both only depend on Step 1. 
--         We verify Steps 2 and 3 get the same level (2), meaning the scheduler knows to run them in parallel.
-- ============================================================
INSERT INTO test_results
WITH RECURSIVE
t_dep AS (
    SELECT 98 AS UNIT_NBR, 1 AS RULE_ID, 1 AS STEP_SEQ_ID, 0 AS STEP_DEP_ID
    UNION ALL SELECT 98,2,2,1 UNION ALL SELECT 98,3,3,1
),
edges AS (SELECT UNIT_NBR, STEP_DEP_ID parent_step, STEP_SEQ_ID child_step FROM t_dep WHERE STEP_DEP_ID<>0),
roots AS (SELECT DISTINCT UNIT_NBR, STEP_SEQ_ID step_id, 1 lvl FROM t_dep WHERE STEP_DEP_ID=0),
traversal AS (
    SELECT unit_nbr, step_id, lvl FROM roots
    UNION ALL
    SELECT e.UNIT_NBR, e.child_step, t.lvl+1 FROM traversal t JOIN edges e ON e.UNIT_NBR=t.UNIT_NBR AND e.parent_step=t.step_id
),
final_levels AS (SELECT UNIT_NBR, step_id, MAX(lvl) PARALLEL_LEVEL FROM traversal GROUP BY UNIT_NBR, step_id)
SELECT 'T02 Two parallel branches from root',
    IF(
        (SELECT PARALLEL_LEVEL FROM final_levels WHERE step_id=1)=1 AND
        (SELECT PARALLEL_LEVEL FROM final_levels WHERE step_id=2)=2 AND
        (SELECT PARALLEL_LEVEL FROM final_levels WHERE step_id=3)=2,
        'PASS','FAIL');

-- ============================================================
-- T03  –  Diamond: 1→2→4, 1→3→4
--         Expected: 1=1, 2=2, 3=2, 4=3
--         Step 1 splits into two parallel branches (Steps 2 and 3), then both must finish before Step 4 can start. 
--         This diamond pattern is the most common real-world dependency shape. We verify Step 4 waits for both branches (2 and 3).
-- ============================================================
INSERT INTO test_results
WITH RECURSIVE
t_dep AS (
    SELECT 97 AS UNIT_NBR, 1 AS RULE_ID, 1 AS STEP_SEQ_ID, 0 AS STEP_DEP_ID
    UNION ALL SELECT 97,2,2,1 UNION ALL SELECT 97,3,3,1
    UNION ALL SELECT 97,4,4,2 UNION ALL SELECT 97,5,4,3
),
edges AS (SELECT UNIT_NBR, STEP_DEP_ID parent_step, STEP_SEQ_ID child_step FROM t_dep WHERE STEP_DEP_ID<>0),
roots AS (SELECT DISTINCT UNIT_NBR, STEP_SEQ_ID step_id, 1 lvl FROM t_dep WHERE STEP_DEP_ID=0),
traversal AS (
    SELECT unit_nbr, step_id, lvl FROM roots
    UNION ALL
    SELECT e.UNIT_NBR, e.child_step, t.lvl+1 FROM traversal t JOIN edges e ON e.UNIT_NBR=t.UNIT_NBR AND e.parent_step=t.step_id
),
final_levels AS (SELECT UNIT_NBR, step_id, MAX(lvl) PARALLEL_LEVEL FROM traversal GROUP BY UNIT_NBR, step_id)
SELECT 'T03 Diamond fan-out/fan-in',
    IF(
        (SELECT PARALLEL_LEVEL FROM final_levels WHERE step_id=1)=1 AND
        (SELECT PARALLEL_LEVEL FROM final_levels WHERE step_id=2)=2 AND
        (SELECT PARALLEL_LEVEL FROM final_levels WHERE step_id=3)=2 AND
        (SELECT PARALLEL_LEVEL FROM final_levels WHERE step_id=4)=3,
        'PASS','FAIL');

-- ============================================================
-- T04  –  Single isolated step
--         Expected: 1=1, exactly 1 row
--         A job with just one step and no dependencies. We verify the resolver doesn't crash on a singular input and correctly assigns level 1, and that exactly one row comes back.
-- ============================================================
INSERT INTO test_results
WITH RECURSIVE
t_dep AS (SELECT 96 AS UNIT_NBR, 1 AS RULE_ID, 1 AS STEP_SEQ_ID, 0 AS STEP_DEP_ID),
edges AS (SELECT UNIT_NBR, STEP_DEP_ID parent_step, STEP_SEQ_ID child_step FROM t_dep WHERE STEP_DEP_ID<>0),
roots AS (SELECT DISTINCT UNIT_NBR, STEP_SEQ_ID step_id, 1 lvl FROM t_dep WHERE STEP_DEP_ID=0),
traversal AS (
    SELECT unit_nbr, step_id, lvl FROM roots
    UNION ALL
    SELECT e.UNIT_NBR, e.child_step, t.lvl+1 FROM traversal t JOIN edges e ON e.UNIT_NBR=t.UNIT_NBR AND e.parent_step=t.step_id
),
final_levels AS (SELECT UNIT_NBR, step_id, MAX(lvl) PARALLEL_LEVEL FROM traversal GROUP BY UNIT_NBR, step_id)
SELECT 'T04 Single isolated step',
    IF(
        (SELECT COUNT(*) FROM final_levels)=1 AND
        (SELECT PARALLEL_LEVEL FROM final_levels WHERE step_id=1)=1,
        'PASS','FAIL');

-- ============================================================
-- T05  –  Multiple independent roots
--         Root A: 1→3, Root B: 2→4
--         Expected: 1=1, 2=1, 3=2, 4=2
--         Two completely separate chains that share no dependencies at all. Both Chain A (1→3) and Chain B (2→4) start at level 1 independently. 
--         We verify the resolver handles multiple entry points and doesn't mix up the two chains.
-- ============================================================
INSERT INTO test_results
WITH RECURSIVE
t_dep AS (
    SELECT 95 AS UNIT_NBR, 1 AS RULE_ID, 1 AS STEP_SEQ_ID, 0 AS STEP_DEP_ID
    UNION ALL SELECT 95,2,2,0 UNION ALL SELECT 95,3,3,1 UNION ALL SELECT 95,4,4,2
),
edges AS (SELECT UNIT_NBR, STEP_DEP_ID parent_step, STEP_SEQ_ID child_step FROM t_dep WHERE STEP_DEP_ID<>0),
roots AS (SELECT DISTINCT UNIT_NBR, STEP_SEQ_ID step_id, 1 lvl FROM t_dep WHERE STEP_DEP_ID=0),
traversal AS (
    SELECT unit_nbr, step_id, lvl FROM roots
    UNION ALL
    SELECT e.UNIT_NBR, e.child_step, t.lvl+1 FROM traversal t JOIN edges e ON e.UNIT_NBR=t.UNIT_NBR AND e.parent_step=t.step_id
),
final_levels AS (SELECT UNIT_NBR, step_id, MAX(lvl) PARALLEL_LEVEL FROM traversal GROUP BY UNIT_NBR, step_id)
SELECT 'T05 Multiple independent root chains',
    IF(
        (SELECT PARALLEL_LEVEL FROM final_levels WHERE step_id=1)=1 AND
        (SELECT PARALLEL_LEVEL FROM final_levels WHERE step_id=2)=1 AND
        (SELECT PARALLEL_LEVEL FROM final_levels WHERE step_id=3)=2 AND
        (SELECT PARALLEL_LEVEL FROM final_levels WHERE step_id=4)=2,
        'PASS','FAIL');

-- ============================================================
-- T06  –  Critical path beats shortcut edge
--         1→2→4, 1→3→4, 1→4 (shortcut)
--         Expected level for 4 = 3 (not 2 from shortcut)
--         Step 4 can be reached three ways — via Step 2 (depth 3), via Step 3 (depth 3), or directly from Step 1 (depth 2, the shortcut). 
--         The correct answer is level 3, not 2, because Step 4 must wait for Steps 2 and 3 to finish first. We verify the resolver always picks the longest path, not the shortest.
-- ============================================================
INSERT INTO test_results
WITH RECURSIVE
t_dep AS (
    SELECT 94 AS UNIT_NBR, 1 AS RULE_ID, 1 AS STEP_SEQ_ID, 0 AS STEP_DEP_ID
    UNION ALL SELECT 94,2,2,1 UNION ALL SELECT 94,3,3,1
    UNION ALL SELECT 94,4,4,2 UNION ALL SELECT 94,5,4,3 UNION ALL SELECT 94,6,4,1
),
edges AS (SELECT UNIT_NBR, STEP_DEP_ID parent_step, STEP_SEQ_ID child_step FROM t_dep WHERE STEP_DEP_ID<>0),
roots AS (SELECT DISTINCT UNIT_NBR, STEP_SEQ_ID step_id, 1 lvl FROM t_dep WHERE STEP_DEP_ID=0),
traversal AS (
    SELECT unit_nbr, step_id, lvl FROM roots
    UNION ALL
    SELECT e.UNIT_NBR, e.child_step, t.lvl+1 FROM traversal t JOIN edges e ON e.UNIT_NBR=t.UNIT_NBR AND e.parent_step=t.step_id
),
final_levels AS (SELECT UNIT_NBR, step_id, MAX(lvl) PARALLEL_LEVEL FROM traversal GROUP BY UNIT_NBR, step_id)
SELECT 'T06 Critical path wins over shortcut edge',
    IF((SELECT PARALLEL_LEVEL FROM final_levels WHERE step_id=4)=3,'PASS','FAIL');

-- ============================================================
-- T07  –  Multi-unit isolation
--         Unit 1: 1→2 (2 steps), Unit 2: 1→2→3 (3 steps)
--         Two separate batch jobs (Unit 1 and Unit 2) running in the same database. 
--         We verify that steps from Unit 1 never bleed into Unit 2's execution plan and vice versa. Unit 1 should have exactly 2 steps, Unit 2 should have exactly 3, no mixing.
-- ============================================================
INSERT INTO test_results
WITH RECURSIVE
t_dep AS (
    SELECT 1 AS UNIT_NBR, 1 AS RULE_ID, 1 AS STEP_SEQ_ID, 0 AS STEP_DEP_ID
    UNION ALL SELECT 1,2,2,1
    UNION ALL SELECT 2,1,1,0 UNION ALL SELECT 2,2,2,1 UNION ALL SELECT 2,3,3,2
),
edges AS (SELECT UNIT_NBR, STEP_DEP_ID parent_step, STEP_SEQ_ID child_step FROM t_dep WHERE STEP_DEP_ID<>0),
roots AS (SELECT DISTINCT UNIT_NBR, STEP_SEQ_ID step_id, 1 lvl FROM t_dep WHERE STEP_DEP_ID=0),
traversal AS (
    SELECT unit_nbr, step_id, lvl FROM roots
    UNION ALL
    SELECT e.UNIT_NBR, e.child_step, t.lvl+1 FROM traversal t JOIN edges e ON e.UNIT_NBR=t.UNIT_NBR AND e.parent_step=t.step_id
),
final_levels AS (SELECT UNIT_NBR, step_id, MAX(lvl) PARALLEL_LEVEL FROM traversal GROUP BY UNIT_NBR, step_id)
SELECT 'T07 Multi-unit isolation',
    IF(
        (SELECT COUNT(*) FROM final_levels WHERE UNIT_NBR=1)=2 AND
        (SELECT COUNT(*) FROM final_levels WHERE UNIT_NBR=2)=3 AND
        (SELECT PARALLEL_LEVEL FROM final_levels WHERE UNIT_NBR=2 AND step_id=3)=3,
        'PASS','FAIL');

-- ============================================================
-- T08  –  Full acceptance test
--         Exact expected PARALLEL_LEVEL per step for UNIT_NBR=1
--         From the assignment, all 13 stored procedures for UNIT_NBR=1 are loaded and we verify every single step lands on exactly the right level.
-- ============================================================
INSERT INTO test_results
WITH RECURSIVE
t_dep AS (
    SELECT 1 U, 1  R, 1  S, 0  D UNION ALL SELECT 1, 2, 2, 1  UNION ALL SELECT 1, 3, 3, 2
    UNION ALL SELECT 1, 4, 4, 2  UNION ALL SELECT 1, 5, 5, 3  UNION ALL SELECT 1, 6, 5, 4
    UNION ALL SELECT 1, 7, 6, 3  UNION ALL SELECT 1, 8, 6, 4  UNION ALL SELECT 1, 9, 7, 3
    UNION ALL SELECT 1,10, 7, 4  UNION ALL SELECT 1,11, 8, 3  UNION ALL SELECT 1,12, 9, 3
    UNION ALL SELECT 1,13, 8, 4  UNION ALL SELECT 1,14, 9, 4  UNION ALL SELECT 1,15,10, 5
    UNION ALL SELECT 1,16,10, 6  UNION ALL SELECT 1,17,10, 7  UNION ALL SELECT 1,18,10, 8
    UNION ALL SELECT 1,19,10, 9  UNION ALL SELECT 1,20,11,10  UNION ALL SELECT 1,21,12,11
    UNION ALL SELECT 1,22,13,12
),
edges AS (SELECT U UNIT_NBR, D parent_step, S child_step FROM t_dep WHERE D<>0),
roots AS (SELECT DISTINCT U UNIT_NBR, S step_id, 1 lvl FROM t_dep WHERE D=0),
traversal AS (
    SELECT unit_nbr, step_id, lvl FROM roots
    UNION ALL
    SELECT e.UNIT_NBR, e.child_step, t.lvl+1 FROM traversal t JOIN edges e ON e.UNIT_NBR=t.UNIT_NBR AND e.parent_step=t.step_id
),
final_levels AS (SELECT UNIT_NBR, step_id, MAX(lvl) PARALLEL_LEVEL FROM traversal GROUP BY UNIT_NBR, step_id),
r AS (SELECT step_id, PARALLEL_LEVEL FROM final_levels WHERE UNIT_NBR=1)
SELECT 'T08 Full acceptance test (assignment data)',
    IF(
        (SELECT PARALLEL_LEVEL FROM r WHERE step_id=1 )=1 AND
        (SELECT PARALLEL_LEVEL FROM r WHERE step_id=2 )=2 AND
        (SELECT PARALLEL_LEVEL FROM r WHERE step_id=3 )=3 AND
        (SELECT PARALLEL_LEVEL FROM r WHERE step_id=4 )=3 AND
        (SELECT PARALLEL_LEVEL FROM r WHERE step_id=5 )=4 AND
        (SELECT PARALLEL_LEVEL FROM r WHERE step_id=6 )=4 AND
        (SELECT PARALLEL_LEVEL FROM r WHERE step_id=7 )=4 AND
        (SELECT PARALLEL_LEVEL FROM r WHERE step_id=8 )=4 AND
        (SELECT PARALLEL_LEVEL FROM r WHERE step_id=9 )=4 AND
        (SELECT PARALLEL_LEVEL FROM r WHERE step_id=10)=5 AND
        (SELECT PARALLEL_LEVEL FROM r WHERE step_id=11)=6 AND
        (SELECT PARALLEL_LEVEL FROM r WHERE step_id=12)=7 AND
        (SELECT PARALLEL_LEVEL FROM r WHERE step_id=13)=8,
        'PASS','FAIL');

-- ============================================================
-- T09  –  Step count integrity (exactly 13 rows for UNIT 1)
--         We verify the resolver returns exactly 13 rows for UNIT_NBR=1, one per step. Guards against bugs/duplications where steps are accidentally duplicated or dropped from the output.
-- ============================================================
INSERT INTO test_results
WITH RECURSIVE
t_dep AS (
    SELECT 1 U, 1  R, 1  S, 0  D UNION ALL SELECT 1, 2, 2, 1  UNION ALL SELECT 1, 3, 3, 2
    UNION ALL SELECT 1, 4, 4, 2  UNION ALL SELECT 1, 5, 5, 3  UNION ALL SELECT 1, 6, 5, 4
    UNION ALL SELECT 1, 7, 6, 3  UNION ALL SELECT 1, 8, 6, 4  UNION ALL SELECT 1, 9, 7, 3
    UNION ALL SELECT 1,10, 7, 4  UNION ALL SELECT 1,11, 8, 3  UNION ALL SELECT 1,12, 9, 3
    UNION ALL SELECT 1,13, 8, 4  UNION ALL SELECT 1,14, 9, 4  UNION ALL SELECT 1,15,10, 5
    UNION ALL SELECT 1,16,10, 6  UNION ALL SELECT 1,17,10, 7  UNION ALL SELECT 1,18,10, 8
    UNION ALL SELECT 1,19,10, 9  UNION ALL SELECT 1,20,11,10  UNION ALL SELECT 1,21,12,11
    UNION ALL SELECT 1,22,13,12
),
edges AS (SELECT U UNIT_NBR, D parent_step, S child_step FROM t_dep WHERE D<>0),
roots AS (SELECT DISTINCT U UNIT_NBR, S step_id, 1 lvl FROM t_dep WHERE D=0),
traversal AS (
    SELECT unit_nbr, step_id, lvl FROM roots
    UNION ALL
    SELECT e.UNIT_NBR, e.child_step, t.lvl+1 FROM traversal t JOIN edges e ON e.UNIT_NBR=t.UNIT_NBR AND e.parent_step=t.step_id
),
final_levels AS (SELECT UNIT_NBR, step_id, MAX(lvl) PARALLEL_LEVEL FROM traversal GROUP BY UNIT_NBR, step_id)
SELECT 'T09 Step count integrity (13 unique steps)',
    IF((SELECT COUNT(*) FROM final_levels WHERE UNIT_NBR=1)=13,'PASS','FAIL');

-- ============================================================
-- T10  –  Ordering invariant: no step at level <= its parent
--         For every single dependency rule in the data, we check that the child step's level is always strictly greater than its parent's level. 
--         No step is ever scheduled to run before something it depends on. If any violation is found the test fails.
-- ============================================================
INSERT INTO test_results
WITH RECURSIVE
t_dep AS (
    SELECT 1 U, 1  R, 1  S, 0  D UNION ALL SELECT 1, 2, 2, 1  UNION ALL SELECT 1, 3, 3, 2
    UNION ALL SELECT 1, 4, 4, 2  UNION ALL SELECT 1, 5, 5, 3  UNION ALL SELECT 1, 6, 5, 4
    UNION ALL SELECT 1, 7, 6, 3  UNION ALL SELECT 1, 8, 6, 4  UNION ALL SELECT 1, 9, 7, 3
    UNION ALL SELECT 1,10, 7, 4  UNION ALL SELECT 1,11, 8, 3  UNION ALL SELECT 1,12, 9, 3
    UNION ALL SELECT 1,13, 8, 4  UNION ALL SELECT 1,14, 9, 4  UNION ALL SELECT 1,15,10, 5
    UNION ALL SELECT 1,16,10, 6  UNION ALL SELECT 1,17,10, 7  UNION ALL SELECT 1,18,10, 8
    UNION ALL SELECT 1,19,10, 9  UNION ALL SELECT 1,20,11,10  UNION ALL SELECT 1,21,12,11
    UNION ALL SELECT 1,22,13,12
),
edges AS (SELECT U UNIT_NBR, D parent_step, S child_step FROM t_dep WHERE D<>0),
roots AS (SELECT DISTINCT U UNIT_NBR, S step_id, 1 lvl FROM t_dep WHERE D=0),
traversal AS (
    SELECT unit_nbr, step_id, lvl FROM roots
    UNION ALL
    SELECT e.UNIT_NBR, e.child_step, t.lvl+1 FROM traversal t JOIN edges e ON e.UNIT_NBR=t.UNIT_NBR AND e.parent_step=t.step_id
),
final_levels AS (SELECT UNIT_NBR, step_id, MAX(lvl) PARALLEL_LEVEL FROM traversal GROUP BY UNIT_NBR, step_id),
violations AS (
    SELECT fl_c.step_id
    FROM   t_dep d
    JOIN   final_levels fl_c ON fl_c.UNIT_NBR=d.U AND fl_c.step_id=d.S
    JOIN   final_levels fl_p ON fl_p.UNIT_NBR=d.U AND fl_p.step_id=d.D
    WHERE  d.D <> 0
      AND  fl_c.PARALLEL_LEVEL <= fl_p.PARALLEL_LEVEL
)
SELECT 'T10 No step runs before its dependency',
    IF((SELECT COUNT(*) FROM violations)=0,'PASS','FAIL');

-- ============================================================
-- RESULTS SUMMARY
-- ============================================================
SELECT
    test_name,
    status,
    IF(status='PASS','✓','✗') AS result
FROM   test_results
ORDER BY test_name;

SELECT
    COUNT(*)                                                      AS total_tests,
    SUM(IF(status='PASS',1,0))                                    AS passed,
    SUM(IF(status='FAIL',1,0))                                    AS failed,
    CONCAT(ROUND(100*SUM(IF(status='PASS',1,0))/COUNT(*),0),'%') AS pass_rate
FROM test_results;
