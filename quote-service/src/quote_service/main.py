"""Import-safe CLI entry point: nothing starts at module level.

python -m quote_service.main LATTE 2 [EUR|USD]
"""

import sys

from pico_boot import init
from pico_pydantic import ValidationFailedError

from quote_service.app import QuoteService


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: quote_service SKU QUANTITY [CURRENCY]", file=sys.stderr)
        return 2
    request = {
        "sku": argv[0],
        "quantity": argv[1],
        "currency": argv[2] if len(argv) > 2 else "EUR",
    }
    # pico-boot discovers the installed pico-pydantic plugin: no module list to maintain
    container = init(modules=["quote_service"])
    try:
        quote = container.get(QuoteService).quote(request)
    except ValidationFailedError as exc:
        print(f"rejected: {exc}", file=sys.stderr)
        return 1
    finally:
        container.shutdown()
    print(quote.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
