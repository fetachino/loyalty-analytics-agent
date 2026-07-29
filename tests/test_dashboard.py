from fastapi.testclient import TestClient


def test_dashboard_is_served(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Loyalty Intelligence" in response.text
    assert "/api/v1/agent/query" not in response.text
    assert response.headers["content-type"].startswith("text/html")
    assert 'id="login-form"' in response.text
    assert 'id="logout-button"' in response.text
    assert 'id="manage"' in response.text
    assert 'id="customer-create-form"' in response.text
    assert 'id="customer-update-form"' in response.text
    assert 'id="transaction-create-form"' in response.text
    assert 'id="reward-create-form"' in response.text


def test_dashboard_assets_are_served(client: TestClient) -> None:
    stylesheet = client.get("/static/styles.css")
    javascript = client.get("/static/app.js")
    assert stylesheet.status_code == 200
    assert "--forest: #173f35" in stylesheet.text
    assert javascript.status_code == 200
    assert 'agent: "/api/v1/agent/query"' in javascript.text
    assert 'createCustomer: "/api/v1/admin/customers"' in javascript.text
    assert 'createTransaction: "/api/v1/admin/transactions"' in javascript.text
    assert 'createReward: "/api/v1/admin/rewards"' in javascript.text
    assert 'document.querySelector("#manage").hidden = !user.is_admin' in javascript.text
