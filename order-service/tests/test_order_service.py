import pytest


@pytest.fixture
def client(make_container, make_client, tmp_path):
    container = make_container(
        "pico_fastapi",
        "pico_sqlalchemy",
        config={
            "fastapi": {"title": "orders"},
            "database": {"url": f"sqlite+aiosqlite:///{tmp_path}/orders.db"},
        },
    )
    return make_client(container)


def test_place_and_list_orders(client):
    r = client.post("/api/v1/orders", json={"sku": "LATTE", "quantity": 2})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["amount_cents"] == 780 and body["status"] == "placed"

    orders = client.get("/api/v1/orders").json()
    assert orders == [{"id": body["id"], "sku": "LATTE", "quantity": 2}]


def test_validation_rejects_bad_quantity(client):
    assert client.post("/api/v1/orders", json={"sku": "LATTE", "quantity": 0}).status_code == 422


def test_out_of_stock_rolls_the_row_back(client):
    # the service inserts BEFORE reserving stock; the 409 proves the raise,
    # the empty list proves @transactional rolled the insert back
    r = client.post("/api/v1/orders", json={"sku": "LATTE", "quantity": 999})
    assert r.status_code == 409
    assert client.get("/api/v1/orders").json() == []
