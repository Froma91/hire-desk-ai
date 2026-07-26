# Implementation Plan: hire-desk-ai-mvp

## Overview

Incremental build of PROJECT_HIRE_DESK_AI in dependency order: project scaffold
→ SAM infrastructure → DynamoDB layer → Applications CRUD API → Vue frontend
foundation → application UI → Kanban board → dashboard → next-action engine →
Bedrock analysis → manual fallback → tests → AWS deployment → demo prep.

All AWS calls stay in Lambda (never in the browser). `userId` is always
`"demo-user"`. Only two Lambda functions are used: `ApplicationsFunction` and
`JobAnalysisFunction`. One DynamoDB table: `ApplicationsTable`.

---

## Tasks

- [ ] 1. Project structure and local development setup
  - [ ] 1.1 Create backend directory layout
    - Create `backend/applications_function/` with empty `app.py`, `handlers/`, `services/`, `repositories/`, `validators/`, `business_rules/` sub-packages (each with `__init__.py`)
    - Create `backend/job_analysis_function/` with empty `app.py`, `handlers/`, `services/`, `validators/` sub-packages (each with `__init__.py`)
    - Create `backend/tests/unit/` and `backend/tests/integration/` directories with `__init__.py` files
    - Create `backend/requirements.txt` pinning `boto3`, `botocore`, and `hypothesis`
    - Create `backend/requirements-dev.txt` pinning `pytest`, `pytest-cov`, `hypothesis`, `moto`
    - _Requirements: 9.1_

  - [ ] 1.2 Create frontend scaffold with Vite + Vue 3 + TypeScript
    - Run `npm create vue@latest` (or equivalent) with Vue Router, Pinia, TypeScript, Vitest enabled
    - Create `frontend/src/api/client.ts` as an empty module
    - Create `frontend/src/stores/` directory with empty `applications.ts`, `stats.ts`, `ui.ts` store files
    - Create `frontend/src/views/` with empty `BoardView.vue`, `DashboardView.vue`, `NewApplicationView.vue`
    - Create `frontend/src/components/` with empty placeholder files for `NavBar.vue`, `KanbanBoard.vue`, `KanbanColumn.vue`, `ApplicationCard.vue`, `JobDescriptionForm.vue`, `ExtractionReviewForm.vue`, `DashboardStats.vue`, `NotificationToast.vue`
    - Add `VITE_API_BASE_URL` to `frontend/.env.local` pointing to `http://localhost:3000`
    - _Requirements: 7.1, 7.2_

- [ ] 2. Minimal AWS SAM infrastructure
  - [ ] 2.1 Write `template.yaml` with DynamoDB table and two Lambda functions
    - Define `ApplicationsTable` with `userId` (S, partition key) and `applicationId` (S, sort key), `PAY_PER_REQUEST` billing
    - Define `ApplicationsFunction` (Python 3.12, `app.handler`, 512 MB, 30 s timeout) with `TABLE_NAME` and `LOG_LEVEL` environment variables; attach least-privilege DynamoDB policy scoped to `ApplicationsTable`
    - Define `JobAnalysisFunction` (Python 3.12, `app.handler`, 512 MB, 60 s timeout) with `TABLE_NAME`, `BEDROCK_MODEL_ID`, and `LOG_LEVEL` env vars; attach least-privilege Bedrock `InvokeModel` + DynamoDB read policies
    - Define `HttpApi` (API Gateway HTTP API) with routes for all 9 endpoints mapped to the correct Lambda; add `ApiUrl` output
    - _Requirements: 9.1, 9.2, 9.3, 9.5, 9.6_

  - [ ]* 2.2 Verify SAM template passes validation
    - Run `sam validate --lint` locally and confirm zero errors
    - _Requirements: 9.1_

- [ ] 3. DynamoDB repository and backend validation
  - [ ] 3.1 Implement Python domain models
    - Write `Status`, `Priority`, `StatusEntry`, `NextAction`, `Application`, `ExtractionResult`, `DashboardStats` dataclasses and enums in `applications_function/models.py`
    - _Requirements: 3.1, 3.5_

  - [ ] 3.2 Implement `applications_repo.py`
    - Write `ApplicationsRepo` class with methods: `put(app)`, `get(applicationId)`, `list_all()`, `update(applicationId, fields)`, `delete(applicationId)`
    - Use `boto3` with `botocore.config.Config(connect_timeout=5, read_timeout=5)`
    - `list_all()` queries `userId = "demo-user"` and returns items ordered by `createdAt` descending
    - Raise typed `RepositoryError` on `ClientError` or timeout (maps to HTTP 503)
    - Raise `NotFoundError` when `GetItem`/`DeleteItem` condition fails (maps to HTTP 404)
    - Read `TABLE_NAME` from environment variable; never accept table name from caller
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.7, 3.8, 3.9, 3.10_

  - [ ] 3.3 Implement `payload_validator.py`
    - Write `validate_application_payload(data)` enforcing: `jobTitle` non-empty; all string fields ≤ 500 chars; all list items ≤ 200 chars; no list > 30 items; payload contains no DynamoDB identifiers (`TableName`, `IndexName`, etc.)
    - Return `(True, None)` on success; `(False, {field, reason})` on failure
    - _Requirements: 2.6, 2.7, 8.2, 8.3_

  - [ ]* 3.4 Write property test for `validate_application_payload`
    - **Property 4: Lambda field validation accepts iff all constraints satisfied**
    - **Validates: Requirements 2.6, 2.7, 8.2, 8.3**
    - File: `backend/tests/unit/test_payload_validator.py`
    - Use pytest example-based tests covering all rejection branches and a valid payload
    - _Requirements: 2.6, 2.7, 8.2, 8.3_

- [ ] 4. Applications CRUD API
  - [ ] 4.1 Implement `applications_service.py`
    - Write `create_application(data)`: validate payload, generate UUID v4 `applicationId`, set `userId = "demo-user"`, set `createdAt` / `updatedAt` / `statusHistory`, call `repo.put()`
    - Write `list_applications()`: call `repo.list_all()`
    - Write `get_application(applicationId)`: call `repo.get()`; raise `NotFoundError` if missing
    - Write `update_application(applicationId, data)`: validate partial payload, call `repo.update()`
    - Write `delete_application(applicationId)`: call `repo.delete()`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8_

  - [ ] 4.2 Implement CRUD handlers in `handlers/applications.py`
    - Write `create_application`, `list_applications`, `get_application`, `update_application`, `delete_application` handler functions
    - Each handler parses the API Gateway event, calls the service, and returns an HTTP response dict with correct status code and JSON body
    - Map `NotFoundError` → 404, `ValidationError` → 400, `RepositoryError` → 503, unhandled exceptions → 500
    - Use the Lambda error response envelope `{"error": {"code", "message", "field?"}}`
    - _Requirements: 3.1–3.10, 8.2, 8.3, 8.5_

  - [ ] 4.3 Implement `app.py` dispatcher for `ApplicationsFunction`
    - Parse `httpMethod` and `resource`/`routeKey` from the event and route to the correct handler
    - Include a catch-all that returns 404 for unrecognised routes
    - _Requirements: 9.1_

  - [ ] 4.4 Write unit tests for CRUD handlers
    - File: `backend/tests/unit/test_applications_handlers.py`
    - Mock `ApplicationsRepo` with `unittest.mock`
    - Cover: happy-path create (201 + UUID in response), list (200 ordered), get (200), update partial fields only (Property 6: partial update preserves unmodified fields — **Validates: Requirements 3.5**), delete (204), not-found (404), validation error (400)
    - Verify `applicationId` is server-generated UUID absent from request body (Property 5 — **Validates: Requirements 3.1, 3.3**)
    - Verify list ordering by `createdAt` descending (Property 7 — **Validates: Requirements 3.2**)
    - _Requirements: 3.1–3.10_

  - [ ] 4.5 Checkpoint — CRUD layer
    - Run `pytest backend/tests/unit/test_applications_handlers.py backend/tests/unit/test_payload_validator.py -v`
    - Confirm all tests pass; ask the user if questions arise.

- [ ] 5. Vue frontend foundation and routing
  - [ ] 5.1 Implement `src/router/index.ts`
    - Define three routes: `/board` → `BoardView`, `/dashboard` → `DashboardView`, `/new` → `NewApplicationView`
    - Add catch-all redirect to `/board`
    - _Requirements: 7.1, 7.5_

  - [ ] 5.2 Implement `NavBar.vue`
    - Render links to `/board`, `/dashboard`, and `/new`
    - Apply an active CSS class to the link matching the current `$route.path`
    - Include `NavBar` in `App.vue` so it persists across all routes
    - _Requirements: 7.3, 7.4_

  - [ ] 5.3 Implement `src/api/client.ts`
    - Export `get(path)`, `post(path, body)`, `patch(path, body)`, `del(path)` functions
    - Prefix all requests with `import.meta.env.VITE_API_BASE_URL`
    - Set `Content-Type: application/json` on POST/PATCH
    - Throw typed `ApiError` (with `status` and `message`) on non-2xx responses
    - Apply a 30-second timeout only on calls to `/analyze`
    - Never embed AWS credentials or DynamoDB identifiers
    - _Requirements: 8.1, 1.7_

  - [ ] 5.4 Implement `uiStore` (`src/stores/ui.ts`)
    - State: `notifications: Notification[]`
    - Actions: `notify(message, type)` (adds notification, auto-removes after 5 s, replaces existing), `clearNotification(id)`
    - _Requirements: 4.5_

  - [ ] 5.5 Implement `NotificationToast.vue`
    - Reads from `uiStore.notifications` and renders the current toast
    - Auto-dismiss after 5 seconds; replaces current toast if a new one arrives
    - Never display raw stack traces or AWS internal details
    - Include in `App.vue`
    - _Requirements: 4.5, 8.5_

  - [ ] 5.6 Write routing unit tests
    - File: `frontend/src/__tests__/routing.spec.ts`
    - Verify unknown route redirects to `/board`
    - Verify each named route renders the correct component
    - File: `frontend/src/__tests__/NavBar.spec.ts`
    - Verify all three route links are present
    - Verify active link is highlighted for the current route
    - _Requirements: 7.1, 7.4, 7.5_

- [ ] 6. Application creation and management interface
  - [ ] 6.1 Implement `applicationsStore` (`src/stores/applications.ts`)
    - State: `applications: Application[]`, `loading: boolean`, `error: string | null`
    - Actions: `fetchAll()`, `fetchOne(id)`, `create(data)`, `update(id, data)`, `delete(id)`, `updateStatus(id, status)` — each calls `client.ts` and updates local state; `updateStatus` saves previous status before dispatch for rollback
    - _Requirements: 3.1–3.8, 4.4_

  - [ ] 6.2 Implement `JobDescriptionForm.vue`
    - Render a `<textarea>` limited to 10 000 characters and an "Analyze" button
    - Disable the Analyze button while `jobDescription` is empty or while a request is in flight
    - Reject (do not send) any input exceeding 10 000 characters (Property 1 — **Validates: Requirements 1.1**)
    - On submit emit `analyze(jobDescription)` to parent
    - _Requirements: 1.1_

  - [ ] 6.3 Implement `ExtractionReviewForm.vue`
    - Accept an `ExtractionResult` prop (or empty defaults for manual entry)
    - Render all fields as editable inputs; map `null` values to empty strings (Property 13 — **Validates: Requirements 1.4, 2.1**)
    - Keep the "Confirm" button disabled until `jobTitle` is non-empty (Property 3 — **Validates: Requirements 2.3, 2.8**)
    - On confirm emit `confirm(formData)` to parent; on field change update local state without saving
    - Display inline error message if the parent reports a save failure; keep form data intact
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.8_

  - [ ] 6.4 Implement `NewApplicationView.vue`
    - Mount `JobDescriptionForm` and `ExtractionReviewForm` in sequence
    - Call `POST /analyze` via `client.ts`; on success pre-fill `ExtractionReviewForm`
    - On `/analyze` 408 or 422 or network error: show toast "Analysis failed. Enter details manually." and display blank `ExtractionReviewForm`
    - On confirm call `applicationsStore.create()`; on success redirect to `/board`; on 4xx show inline error preserving form
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 2.4, 2.5_

  - [ ]* 6.5 Write unit tests for JobDescriptionForm and ExtractionReviewForm
    - File: `frontend/src/__tests__/JobDescriptionForm.spec.ts`
    - Verify Analyze button disabled when textarea empty; verify input of > 10 000 chars does not call API (Property 1)
    - File: `frontend/src/__tests__/ExtractionReviewForm.spec.ts`
    - Verify Confirm disabled while jobTitle empty; enabled when non-empty (Property 3)
    - Verify null Extraction_Result fields render as empty strings (Property 13)
    - _Requirements: 1.1, 2.3, 2.8_

- [ ] 7. Kanban board and status updates
  - [ ] 7.1 Implement `KanbanColumn.vue` and `ApplicationCard.vue`
    - `KanbanColumn` receives a `status` prop and a list of `Application` items; renders each as an `ApplicationCard`; shows an empty-state indicator when the list is empty
    - `ApplicationCard` displays `jobTitle`, `company`, `status` badge, and a drag handle; emits a `drop(applicationId, newStatus)` event when dragged to a new column
    - _Requirements: 4.1, 4.2, 4.3_

  - [ ] 7.2 Implement `KanbanBoard.vue`
    - Render exactly five `KanbanColumn` components (Wishlist, Applied, Interview, Offer, Rejected) sourced from `applicationsStore.applications`
    - On drag-drop: call `applicationsStore.updateStatus(id, newStatus)` — optimistic move within 500 ms, rollback + toast on error (Property 8 — card in correct column — **Validates: Requirements 4.2**)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ] 7.3 Wire `BoardView.vue`
    - On mount call `applicationsStore.fetchAll()`; pass results to `KanbanBoard`
    - Show loading indicator while fetching; show error banner (no stale data) on fetch failure
    - _Requirements: 4.2, 3.2_

  - [ ] 7.4 Implement `update_status` handler in `handlers/status.py`
    - Validate incoming `status` value is one of the five valid enum values; return 400 if invalid (Property 9 — **Validates: Requirements 4.6**)
    - Call `UpdateItem` to persist new status, append entry to `statusHistory`, update `updatedAt`
    - Immediately call `compute_next_action()` and write the result back to `nextAction` field
    - Return full updated `Application` record (200)
    - _Requirements: 4.4, 4.6, 4.7, 6.9_

  - [ ]* 7.5 Write unit tests for status handler and Kanban board
    - File: `backend/tests/unit/test_status_handler.py`
    - Cover: valid status update returns 200 + updated `nextAction`, invalid status returns 400 without DDB call (Property 9), `nextAction` recomputed after status change (Property 11 recompute)
    - File: `frontend/src/__tests__/KanbanBoard.spec.ts`
    - Verify exactly 5 columns rendered; each card appears in column matching its status (Property 8); empty column shows empty-state; optimistic move fires PATCH and rollback shown on error
    - _Requirements: 4.1–4.7_

  - [ ] 7.6 Checkpoint — Kanban board end-to-end
    - Run `pytest backend/tests/unit/test_status_handler.py -v` and `npx vitest run src/__tests__/KanbanBoard.spec.ts`
    - Confirm all tests pass; ask the user if questions arise.

- [ ] 8. Dashboard statistics
  - [ ] 8.1 Implement `stats_service.py` with `compute_stats(applications, now)`
    - Pure function that receives a list of `Application` objects and current UTC datetime
    - Returns `DashboardStats` with `total`, `byStatus` dict (all five statuses, zero-filled), and `currentWeek` (Monday 00:00 UTC – Sunday 23:59 UTC window)
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ] 8.2 Implement `get_stats` handler in `handlers/stats.py`
    - Call `repo.list_all()` then `compute_stats()`; return `DashboardStats` as JSON (200)
    - On `RepositoryError` return 503
    - _Requirements: 5.4, 5.5_

  - [ ]* 8.3 Write property test for `compute_stats`
    - **Property 10: Dashboard stats are consistent with application records**
    - **Validates: Requirements 5.1, 5.2, 5.3**
    - File: `backend/tests/unit/test_compute_stats.py`
    - Use Hypothesis to generate lists of `Application` objects with arbitrary statuses and `createdAt` timestamps
    - Assert `total == len(applications)`, sum of `byStatus.values() == total`, each per-status count matches filtered count, `currentWeek` equals count with `createdAt` in current week window
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ] 8.4 Implement `statsStore` (`src/stores/stats.ts`) and `DashboardStats.vue`
    - `statsStore` state: `stats`, `loading`, `error`; action: `fetchStats()` calls `GET /stats`
    - `DashboardStats.vue` renders total count, per-status counts for all five statuses, and current-week count
    - Show error banner (no stale values) when fetch fails (Property 10 display side — **Validates: Requirements 5.5**)
    - _Requirements: 5.1, 5.2, 5.3, 5.5_

  - [ ] 8.5 Wire `DashboardView.vue`
    - On mount call `statsStore.fetchStats()`; render `DashboardStats` component
    - On error display error message and hide stats
    - _Requirements: 5.4, 5.5_

  - [ ]* 8.6 Write unit tests for DashboardView
    - File: `frontend/src/__tests__/DashboardView.spec.ts`
    - Verify stats are displayed correctly; verify error banner shown when `/stats` fails without stale data
    - _Requirements: 5.1–5.5_

- [ ] 9. Deterministic next-action engine
  - [ ] 9.1 Implement `compute_next_action()` in `business_rules/next_action_engine.py`
    - Pure function signature: `compute_next_action(app: Application, now: datetime) -> Optional[NextAction]`
    - Implement all seven business-rule branches as specified in the design
    - No I/O, no Bedrock calls, no side effects; `explanation` is always `None` here
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.9, 6.10, 6.11_

  - [ ]* 9.2 Write Hypothesis property test for `compute_next_action`
    - **Property 11: Next-action engine is deterministic and status-driven**
    - **Validates: Requirements 6.1–6.6, 6.9–6.11**
    - File: `backend/tests/unit/test_next_action_engine.py`
    - Use Hypothesis `@given` strategies over `Status`, `createdAt`, `updatedAt`, `statusHistory`, and `now`
    - Assert same inputs always produce same output (determinism)
    - Assert each status/age combination produces the exact expected `NextAction` or `None`
    - _Requirements: 6.1–6.6, 6.9–6.11_

  - [ ] 9.3 Implement `recommendation_service.py` and `get_recommendation` handler
    - `recommendation_service.get_recommendation(applicationId)`: read app from DDB, call `compute_next_action()`, return `Next_Action_Recommendation` (without Bedrock explanation at this stage)
    - Write `handlers/recommendation.py` `get_recommendation` handler: return 200 with `Next_Action_Recommendation`; 404 if app not found; 503 on DDB error
    - _Requirements: 6.1, 6.9_

  - [ ] 9.4 Checkpoint — next-action engine
    - Run `pytest backend/tests/unit/test_next_action_engine.py -v`
    - Confirm all Hypothesis tests pass; ask the user if questions arise.

- [ ] 10. Amazon Bedrock job-description analysis
  - [ ] 10.1 Implement `extraction_validator.py` in `job_analysis_function/validators/`
    - Write `validate_extraction_result(raw_dict)`: returns `ExtractionResult` if all required keys present (`jobTitle`, `company`, `location`, `skills`, `responsibilities`, `languages`, `experienceLevel`); raises `ExtractionValidationError` if any key missing
    - (Property 2 — **Validates: Requirements 1.3, 1.6**)
    - _Requirements: 1.3, 1.6_

  - [ ]* 10.2 Write unit tests for `extraction_validator`
    - File: `backend/tests/unit/test_extraction_validator.py`
    - Use pytest example-based tests; cover all-keys-present (accept), each key missing individually (reject), null values accepted
    - _Requirements: 1.3, 1.6_

  - [ ] 10.3 Implement `bedrock_service.py` in `job_analysis_function/services/`
    - Write `analyze_job_description(job_description: str) -> ExtractionResult`
    - Call `boto3` Bedrock `invoke_model` with `claude-3-haiku`; parse response JSON; call `validate_extraction_result()`
    - Enforce 30-second timeout via `botocore.config`; catch `ClientError`, `ReadTimeoutError`, and `ConnectTimeoutError`
    - On timeout raise `BedrockTimeoutError`; on schema validation failure raise `ExtractionValidationError`; on other Bedrock errors raise `BedrockError`
    - Never log job description content; log `requestId` and error type only
    - _Requirements: 1.3, 1.6, 1.7, 1.8, 8.5_

  - [ ] 10.4 Implement `analyze_job` handler in `job_analysis_function/handlers/analysis.py`
    - Parse `jobDescription` from request body; call `bedrock_service.analyze_job_description()`
    - Return 200 `ExtractionResult` on success
    - Map `BedrockTimeoutError` → 408, `ExtractionValidationError` → 422, `BedrockError` → 502
    - _Requirements: 1.2, 1.3, 1.6, 1.7, 1.8_

  - [ ] 10.5 Implement Bedrock explanation in `recommendation_service.py`
    - After `compute_next_action()` returns a non-None result, call `JobAnalysisFunction`'s `bedrock_service` to request a ≤ 280-char explanation
    - If Bedrock response > 280 chars, set `explanation = None`; if Bedrock fails/times out, set `explanation = None` (graceful degradation)
    - Attach explanation to `NextAction.explanation` before returning response
    - (Property 12 — **Validates: Requirements 6.7, 6.8**)
    - _Requirements: 6.7, 6.8_

  - [ ]* 10.6 Write unit tests for analysis handler and Bedrock service
    - File: `backend/tests/unit/test_analysis_handler.py`
    - Mock `bedrock_service` with `unittest.mock`
    - Cover: Bedrock succeeds → 200 `ExtractionResult`; timeout → 408; schema mismatch → 422; Bedrock error → 502
    - Verify `explanation = null` when Bedrock returns > 280 chars or fails (Property 12)
    - _Requirements: 1.3, 1.6–1.8, 6.7, 6.8_

  - [ ] 10.7 Implement `app.py` dispatcher for `JobAnalysisFunction`
    - Route `POST /analyze` → `analyze_job` handler
    - Route `GET /applications/{id}/recommendation` → call `recommendation_service` (reads app from DDB then optionally enriches with Bedrock)
    - Catch-all for unrecognised routes returns 404
    - _Requirements: 9.1_

- [ ] 11. Graceful manual fallback when Bedrock fails
  - [ ] 11.1 Verify fallback behaviour in `NewApplicationView.vue`
    - Confirm that when `POST /analyze` returns 408 or 422 (or any non-2xx), the view switches to the blank manual-entry `ExtractionReviewForm` and shows the toast "Analysis failed. Enter details manually."
    - Confirm that when `GET /applications/{id}/recommendation` returns with `explanation: null`, the `ApplicationCard` or recommendation display renders without an explanation rather than showing an error
    - No new code required if already wired in task 6.4 — verify and add any missing conditional rendering
    - _Requirements: 1.5, 1.6, 1.8, 6.8_

  - [ ] 11.2 Verify Bedrock timeout and error paths in `bedrock_service.py`
    - Confirm `BedrockTimeoutError` maps correctly to 408 in the analysis handler
    - Confirm `ExtractionValidationError` maps to 422
    - Confirm `explanation = null` when Bedrock is unavailable for recommendations
    - No new code required if covered in task 10.3–10.5 — verify test coverage is complete
    - _Requirements: 1.7, 1.8, 6.7, 6.8_

- [ ] 12. Essential tests
  - [ ] 12.1 Complete backend unit test suite
    - Ensure all test files listed in the design's test layout exist and pass:
      `test_next_action_engine.py`, `test_compute_stats.py`, `test_payload_validator.py`, `test_extraction_validator.py`, `test_applications_handlers.py`, `test_status_handler.py`, `test_analysis_handler.py`
    - Run `pytest backend/tests/unit/ -v --tb=short` and fix any failures
    - _Requirements: all backend requirements_

  - [ ] 12.2 Complete frontend unit test suite
    - Ensure all test files listed in the design's test layout exist and pass:
      `JobDescriptionForm.spec.ts`, `ExtractionReviewForm.spec.ts`, `KanbanBoard.spec.ts`, `DashboardView.spec.ts`, `routing.spec.ts`, `NavBar.spec.ts`
    - Run `npx vitest run` from the `frontend/` directory and fix any failures
    - _Requirements: all frontend requirements_

  - [ ]* 12.3 Write integration smoke tests
    - File: `backend/tests/integration/test_api_flows.py`
    - Target a locally running `sam local start-api` instance
    - Cover all 7 flows listed in the design's integration test section
    - Mark with `pytest.mark.integration` so they are excluded from default unit test runs
    - _Requirements: 3.1, 3.2, 3.3, 3.7, 5.1, 4.4_

  - [ ] 12.4 Checkpoint — full test suite
    - Run `pytest backend/tests/unit/ -v` and `npx vitest run` from `frontend/`
    - Confirm zero failures; ask the user if questions arise.

- [ ] 13. AWS deployment
  - [ ] 13.1 Configure `samconfig.toml` for deployment
    - Create `samconfig.toml` at repo root with default stack name, region, S3 bucket for artifacts, and `confirm_changeset = false`
    - Add `BEDROCK_MODEL_ID` default value (`anthropic.claude-3-haiku-20240307-v1:0`) and `LOG_LEVEL = INFO`
    - _Requirements: 9.1, 9.3_

  - [ ] 13.2 Configure frontend build and Amplify Hosting
    - Add `build` script in `frontend/package.json` that sets `VITE_API_BASE_URL` to the SAM stack output URL
    - Create `amplify.yml` at repo root with build commands for the frontend and publish directory `frontend/dist`
    - _Requirements: 9.1_

  - [ ]* 13.3 Verify `sam deploy` produces the expected outputs
    - Run `sam validate --lint` to confirm no template errors
    - Confirm that after `sam deploy`, the `ApiUrl` stack output is present in the CLI output
    - _Requirements: 9.3, 9.6_

- [ ] 14. Demo preparation [OPTIONAL]
  - [ ] 14.1 Create demo seed script
    - Write `scripts/seed_demo_data.py` that calls `POST /applications` with 5–8 sample applications covering all five statuses
    - Script reads API base URL from `API_BASE_URL` environment variable
    - _Requirements: None (demo aid only)_

  - [ ] 14.2 [STRETCH] Add a "Reset demo" button to the frontend
    - Add a UI button (visible only in dev/demo mode via `VITE_DEMO_MODE` flag) that calls `DELETE /applications/{id}` for all loaded applications and re-seeds from a local fixture
    - _Requirements: None (demo aid only)_

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Tasks marked with `[OPTIONAL]` or `[STRETCH]` are non-critical for core demo
- Each task references specific requirements for traceability
- Checkpoints at tasks 4.5, 7.6, 9.4, 12.4 ensure incremental validation
- Hypothesis property-based tests cover `compute_next_action()` (Property 11) and `compute_stats()` (Property 10) only; all other backend tests are example-based with `unittest.mock`
- Frontend tests are all example-based with Vitest + Vue Test Utils (no fast-check)
- The manual-entry fallback (task 11) must remain functional at all times; Bedrock failure must never block the CRUD workflow
- `userId` is always hardcoded to `"demo-user"` — no Cognito, no authentication layer

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["2.1", "3.1"] },
    { "id": 2, "tasks": ["2.2", "3.2", "3.3", "5.1", "5.2", "5.3", "5.4", "5.5"] },
    { "id": 3, "tasks": ["3.4", "4.1", "8.1", "9.1", "10.1"] },
    { "id": 4, "tasks": ["4.2", "4.3", "8.2", "9.3", "10.2", "10.3"] },
    { "id": 5, "tasks": ["4.4", "6.1", "7.4", "8.3", "9.2", "10.4"] },
    { "id": 6, "tasks": ["4.5", "6.2", "6.3", "7.1", "8.4", "8.5", "10.5", "10.6"] },
    { "id": 7, "tasks": ["5.6", "6.4", "6.5", "7.2", "8.6", "10.7"] },
    { "id": 8, "tasks": ["7.3", "7.5", "9.4", "11.1", "11.2"] },
    { "id": 9, "tasks": ["7.6", "12.1", "12.2"] },
    { "id": 10, "tasks": ["12.3", "12.4"] },
    { "id": 11, "tasks": ["13.1", "13.2"] },
    { "id": 12, "tasks": ["13.3"] },
    { "id": 13, "tasks": ["14.1"] },
    { "id": 14, "tasks": ["14.2"] }
  ]
}
```
