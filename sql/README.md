# Batch Job Dependency Resolver

A MySQL 8.0+ solution that resolves stored-procedure execution order for batch jobs, respecting all step dependencies and assigning a `PARALLEL_LEVEL` so that independent steps can run concurrently.

---

## Files

| File | Purpose |
|------|---------|
| `SQL_TEST_1_Solution.sql` | DDL, seed data, main query and stored procedure |
| `SQL_TEST_1_TestCases.sql` | 10 test cases that validate the resolver logic |

---

## Requirements

- MySQL 8.0 or higher (recursive CTEs require 8.0+)
- VS Code with the SQLTools extension, or any MySQL GUI tool
- No third-party libraries required

---

## How It Works

The solution uses a **Recursive Common Table Expression (CTE)**:

| Step | What happens |
|------|-------------|
| **Anchor** | Root steps (STEP_DEP_ID = 0) are assigned PARALLEL_LEVEL = 1 |
| **Recursive** | Each child step gets level = parent level + 1 |
| **Collapse** | Final level = MAX across all incoming paths (critical path rule) |
| **Output** | Join with PROG_NAME for human-readable step names |

The `MAX` collapse is the key insight; a step that depends on multiple parents must wait for the **slowest** parent to finish, so the longest path will always be taken.

---

## Expected Execution Plan for UNIT_NBR = 1

| Level | Steps | Notes |
|-------|-------|-------|
| 1 | Step 1 | Job start |
| 2 | Step 2 | Delete job set |
| 3 | Steps 3, 4 | Static + effective PTF extract (run in parallel) |
| 4 | Steps 5, 6, 7, 8, 9 | Tree A–E (all depend on both steps 3 and 4) |
| 5 | Step 10 | Active portfolio (waits for all trees) |
| 6 | Step 11 | PTF lineage |
| 7 | Step 12 | Summary to bookable RS |
| 8 | Step 13 | Job end |

---

## How to Run

### Run the solution

1. Open `SQL_TEST_1_Solution.sql` in VS Code
2. Connect to your MySQL database via SQLTools
3. Press `Ctrl+Shift+P` → `SQLTools: Run Current File`

This will:
- Create the `PROG_NAME` and `DEPENDENCY_RULES` tables
- Insert the seed data
- Run the main query showing the execution plan
- Create the stored procedure `sp_batch_execution_plan`
- Call the stored procedure for `UNIT_NBR = 1`

### Call the stored procedure manually

```sql
CALL sp_batch_execution_plan(1);     -- single unit
CALL sp_batch_execution_plan(NULL);  -- all units
```

### Run the test suite

1. Open `SQL_TEST_1_TestCases.sql` in VS Code
2. Make sure you are connected to the same MySQL database
3. Press `Ctrl+Shift+P` → `SQLTools: Run Current File`

You should see a results summary like:

```
test_name                                 status  result
T01 Linear chain 1->2->3                  PASS    ✓
T02 Two parallel branches from root       PASS    ✓
T03 Diamond fan-out/fan-in                PASS    ✓
T04 Single isolated step                  PASS    ✓
T05 Multiple independent root chains      PASS    ✓
T06 Critical path wins over shortcut      PASS    ✓
T07 Multi-unit isolation                  PASS    ✓
T08 Full acceptance test (assignment)     PASS    ✓
T09 Step count integrity (13 steps)       PASS    ✓
T10 No step runs before its dependency    PASS    ✓

total_tests  passed  failed  pass_rate
10           10      0       100%
```

---

## Assumptions

**A1. STEP_DEP_ID = 0 means no dependency**

A step with STEP_DEP_ID = 0 is a root node — it has no parent and can start immediately at level 1.

**A2. AND semantics for multiple dependencies**

A step is only ready when ALL of its declared dependencies have completed. For example, steps 3 and 4 must both finish before step 5 can start.

**A3. No cycles in the dependency graph**

The dependency graph is assumed to be a Directed Acyclic Graph (DAG). If a cycle exists, MySQL will exhaust the recursion limit and throw an error.

**A4. DELIMITER is intentionally avoided**

VS Code and most MySQL GUI tools do not support the DELIMITER command. The stored procedure uses a single SELECT body with no internal semicolons, so no DELIMITER change is needed.

**A5. Uniform step duration**

For the purpose of assigning PARALLEL_LEVEL, all steps are treated as taking the same amount of time.

---

## Known Gaps & Improvement Areas

**G1. Cycle Detection**

If two steps accidentally depend on each other, the query will loop forever until MySQL throws a max-recursion error, which is cryptic and hard to debug.

Fix: track the path travelled so far as a string inside the CTE (e.g. `1->2->3`). If a step ID already appears in the path, a cycle exists and a clear human-readable error can be raised immediately.

**G2. Cross-Unit Dependencies**

Each batch job (UNIT_NBR) is treated as completely independent. There is no way to say "Job 2 cannot start until Step 5 of Job 1 has finished."

Fix: add a `DEP_UNIT_NBR` column to DEPENDENCY_RULES so a step in one job can declare a dependency on a step in a different job.

**G3. Uniform Step Duration Assumed**

PARALLEL_LEVEL groups steps into waves (1, 2, 3) but assumes every step takes the same amount of time. In reality one step might take 2 seconds and another 2 hours, making the grouping misleading.

Fix: assign each step an estimated duration and use Critical Path Method (CPM) to calculate the earliest and latest start time for each step. For example, Step 3 takes 2 hours, Step 4 takes 30 minutes, and calculate the actual earliest start time in real time units.

**G4. No Execution Status Tracking**

The solution only plans the order of execution. It has no way to know whether a step has actually started, succeeded, or failed at runtime.

Fix: introduce a JOB_RUN table that records the real-time status of each step (e.g. PENDING, RUNNING, COMPLETED, FAILED) so the scheduler can decide which steps are ready to fire next and operators can monitor or retry failed steps.
