from fastapi.testclient import TestClient

from orders.main import create_app


def test_place_order_returns_a_transport_dto():
    client = TestClient(create_app())
    response = client.post('/orders', json={
        'customer_id': 'c-1',
        'lines': [{'sku': 'BOOK', 'quantity': 2, 'unit_price': '12.50'}],
    })
    assert response.status_code == 201
    body = response.json()
    assert body['customer_id'] == 'c-1'
    assert body['total'] == '25.00'
    assert set(body) == {'id', 'customer_id', 'total'}


def test_business_rule_violation_is_a_422():
    client = TestClient(create_app())
    response = client.post('/orders', json={'customer_id': 'c-1', 'lines': []})
    assert response.status_code == 422
