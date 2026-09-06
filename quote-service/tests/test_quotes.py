import pytest
from pico_pydantic import ValidationFailedError

from quote_service.app import QuoteService
from quote_service.main import main


def test_valid_request_is_priced(make_container):
    service = make_container("pico_pydantic").get(QuoteService)
    quote = service.quote({"sku": "LATTE", "quantity": 2})
    assert quote.total_cents == 780
    assert quote.currency == "EUR"


def test_invalid_arguments_never_reach_the_business_logic(make_container):
    service = make_container("pico_pydantic").get(QuoteService)
    # the unknown sku would raise LookupError inside; validation rejects first
    with pytest.raises(ValidationFailedError) as failure:
        service.quote({"sku": "NOPE", "quantity": 0})
    assert failure.value.method_name == "quote"
    assert "quantity" in str(failure.value)


@pytest.mark.asyncio
async def test_async_method_validates_every_item(make_container):
    service = make_container("pico_pydantic").get(QuoteService)
    quotes = await service.quote_many(
        [
            {"sku": "BAGEL", "quantity": 1},
            {"sku": "JUICE", "quantity": 2, "currency": "USD"},
        ]
    )
    assert [quote.total_cents for quote in quotes] == [250, 924]
    with pytest.raises(ValidationFailedError):
        await service.quote_many(
            [{"sku": "BAGEL", "quantity": 1}, {"sku": "X", "quantity": 1}]
        )


@pytest.mark.pico_auto_plugins
def test_cli_boots_with_plugin_discovery(capsys):
    assert main(["LATTE", "2"]) == 0
    assert '"total_cents":780' in capsys.readouterr().out
    assert main(["LATTE", "zero"]) == 1
