# quote-service

Validation in the service layer, not at the transport: `@validate` on component methods, and a CLI entry point that pico-boot wires without a module list.

What to look at:

- `QuoteService.quote` takes a `QuoteRequest`; callers may pass a dict (the CLI does) and receive a validated model, or a `ValidationFailedError` naming the method. Business code never sees a bad argument.
- `quote_many` is async and typed `list[QuoteRequest]`: every item is validated, one bad item rejects the call.
- `main.py` calls `pico_boot.init(modules=["quote_service"])`: pico-pydantic is discovered because it is installed. The test for it carries `@pytest.mark.pico_auto_plugins`, the pico-testing opt-in for real plugin discovery.

```bash
pip install -e ".[dev]" && pytest
python -m quote_service.main LATTE 2 USD
```
