from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == "Smart Inventory API is running"


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_login_admin():
    response = client.post(
        "/auth/login",
        json={
            "email": "charitha@gmail.com",
            "password": "cherry2004"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_get_current_admin():
    login_response = client.post(
        "/auth/login",
        json={
            "email": "charitha@gmail.com",
            "password": "cherry2004"
        }
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert "email" in data
    assert "role" in data    


def test_create_product():
    # Login
    login_response = client.post(
        "/auth/login",
        json={
            "email": "charitha@gmail.com",
            "password": "cherry2004"
        }
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    # Create product
    response = client.post(
        "/products",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "sku": "TEST-PRODUCT-001",
            "name": "Test Product",
            "category_id": 1,
            "unit": "Piece",
            "cost_price": 100,
            "selling_price": 150,
            "reorder_level": 10,
            "reorder_quantity": 50,
            "barcode": "TEST-BARCODE-003"
        }
    )

    assert response.status_code in [201, 400, 409]

    if response.status_code == 201:
        data = response.json()

        assert data["sku"] == "TEST-PRODUCT-003"
        assert data["name"] == "Test Product 3"    


def test_create_category():
    # Login as Admin
    login_response = client.post(
        "/auth/login",
        json={
            "email": "charitha@gmail.com",
            "password": "cherry2004"
        }
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    # Create category
    response = client.post(
        "/categories",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "category_name": "Test Electronics 2",
            "description": "Category created through automated test"
        }
    )

    assert response.status_code in [201, 400, 409]

    if response.status_code == 201:
        data = response.json()

        assert data["category_name"] == "Test Electronics 2"
        assert "id" in data


def test_create_warehouse():
    # Login as Admin
    login_response = client.post(
        "/auth/login",
        json={
            "email": "charitha@gmail.com",
            "password": "cherry2004"
        }
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    # Create warehouse
    response = client.post(
        "/warehouses",
        headers={
            "Authorization": f"Bearer {token}"
        },
        json={
            "warehouse_code": "TEST-WH-001",
            "name": "Test Warehouse",
            "city": "Hyderabad",
            "address": "Test Address, Hyderabad",
            "capacity": 1000,
            "manager_id": None,
            "is_active": True
        }
    )

    assert response.status_code in [201, 400, 409]

    if response.status_code == 201:
        data = response.json()

        assert data["warehouse_code"] == "TEST-WH-001"
        assert data["name"] == "Test Warehouse"
        assert data["city"] == "Hyderabad"
        assert "id" in data     