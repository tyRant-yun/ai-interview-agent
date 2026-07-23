# Day 7 Code Audit

## Scope

Reviewed:

- notes API
- question generation service
- OpenAI-compatible LLM client
- SSE streaming route
- database test isolation
- fake model dependencies

## Fixed

- removed duplicate imports in interview API tests
- moved FakeLLMClient into a reusable test helper
- added service-level tests
- added model timeout and upstream error tests
- added note update, delete, filter, and persistence tests
- added SSE encoder tests
- corrected outdated LLM client docstring

## Verified

- tests do not call a real model
- tests use an isolated SQLite database
- dependency overrides are cleared after tests
- missing notes fail before model invocation
- missing model configuration fails before SSE starts
- stream errors are sent as SSE error events
- partial stream content is not treated as a completed result
- `.env` and database files are ignored by Git

## Deferred risks

### Upstream error-body exposure

The LLM client currently includes part of the upstream response
body in an exception message. The API may expose this detail to
clients. This should be replaced with internal logging and a
sanitized public message during the reliability phase.

### Client disconnect timing

The streaming route checks disconnect state when an application
update is received. If the upstream stalls, disconnect detection
may not happen immediately.

### Database migrations

The project still uses `create_all()` and has no Alembic migration
history.

### Transaction boundary

Repository write methods currently commit independently. Multi-step
business workflows will eventually require a higher-level
transaction boundary.

### Test client warning

The current Starlette test client emits a dependency deprecation
warning. It does not affect current results but should be tracked.

### Provider compatibility

`response_format`, streaming usage data, and SSE payload details may
differ among OpenAI-compatible providers.

# Day 7 Code Audit

## Completed

- extracted reusable FakeLLMClient
- added API and service-level tests
- covered LLM timeout and upstream failures
- covered SSE errors after partial output
- covered update, delete, filters and persistence
- added SSE encoder tests

## Deferred risks

- upstream error messages may expose provider details
- database schema has no migration history
- repository methods own transaction commits
- client disconnect cancellation is best effort
- provider compatibility differs for JSON mode and streaming usage
