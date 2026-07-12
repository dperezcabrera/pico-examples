# secure-notes

The pico auth pair working end to end in one app: pico-server-auth issues JWTs (login, JWKS, refresh under `/api/v1/auth/*`) and pico-client-auth validates them on every request.

What to look at:

- `NotesController`: `@allow_anonymous` on reads, plain endpoints require a valid token, `@requires_role("admin")` gates deletes.
- The role test mints a token through the app's own `TokenIssuer` with `role="user"`: same issuer, valid signature, still 403 on delete.
- The only stub in the tests is the JWKS fetch (issuer and API are the same in-process app); in production the validator fetches `{issuer}/api/v1/auth/jwks` over HTTP.

```bash
pip install -e ".[dev]" && pytest
```
