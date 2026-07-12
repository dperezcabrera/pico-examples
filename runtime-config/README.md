# runtime-config

Operational hot reload: change behavior of a running instance through `POST /actuator/refresh`, no restart.

What to look at:

- `QuoteService.quote` is `@retryable` against a deliberately flaky feed: with resilience enabled the API returns 200 and the test proves 3 attempts happened underneath.
- Flip `resilience.enabled` in the config source and `POST /actuator/refresh`: the response lists `{"changed": ["resilience"]}` and the very next request fails in a single attempt. Re-enable, refresh again, and retry is back.
- This is the fail-fast philosophy end to end: the policy change is observable, immediate and reversible.

```bash
pip install -e ".[dev]" && pytest
```
