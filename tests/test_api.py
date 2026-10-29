import pytest
from datetime import datetime, timedelta

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data
    assert "redis" in data

def test_auth_flow(client):
    # 1. Signup a test user
    signup_data = {
        "email": "testuser@smartgrid.com",
        "password": "testpassword123",
        "role": "admin",
        "is_active": True
    }
    response = client.post("/api/v1/auth/signup", json=signup_data)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == signup_data["email"]
    assert "id" in data

    # 2. Login to retrieve token
    login_data = {
        "username": "testuser@smartgrid.com",
        "password": "testpassword123"
    }
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

def get_auth_headers(client):
    # Helper to get JWT headers for testing authorized routes
    signup_data = {
        "email": "apiadmin@smartgrid.com",
        "password": "adminsecret123",
        "role": "admin",
        "is_active": True
    }
    client.post("/api/v1/auth/signup", json=signup_data)
    response = client.post("/api/v1/auth/login", data={
        "username": "apiadmin@smartgrid.com",
        "password": "adminsecret123"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_grid_operations_flow(client):
    headers = get_auth_headers(client)
    
    # 1. Create Zone
    zone_data = {
        "name": "Test Zone Alpha",
        "description": "Industrial zone for testing",
        "capacity_limit_kw": 500.0
    }
    response = client.post("/api/v1/zones/", json=zone_data, headers=headers)
    assert response.status_code == 201
    zone_id = response.json()["id"]

    # 2. Create Meter
    meter_data = {
        "serial_number": "MTR-TST-99",
        "zone_id": zone_id,
        "status": "active",
        "capacity_limit_kw": 200.0
    }
    response = client.post("/api/v1/meters/", json=meter_data, headers=headers)
    assert response.status_code == 201
    meter_id = response.json()["id"]

    # 3. Ingest Reading
    reading_data = {
        "meter_id": meter_id,
        "zone_id": zone_id,
        "voltage": 220.5,
        "current": 10.2,
        "power_consumption": 2.25,  # kW
        "frequency": 50.02,
        "temperature": 24.5,
        "timestamp": datetime.now().isoformat()
    }
    # Note: Ingestion endpoint does NOT require auth in our spec (open for meters ingestion)
    response = client.post("/api/v1/meters/readings", json=reading_data)
    assert response.status_code == 201
    assert response.json()["power_consumption"] == 2.25

    # 4. Read Readings
    response = client.get(f"/api/v1/meters/readings?meter_id={meter_id}", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) >= 1

    # 5. Ingest Overload Reading to trigger Alert
    overload_reading = {
        "meter_id": meter_id,
        "zone_id": zone_id,
        "voltage": 218.0,
        "current": 95.0,
        "power_consumption": 185.0,  # 185 kW is > 90% of 200 kW capacity limit!
        "frequency": 49.95,
        "temperature": 32.0,
        "timestamp": datetime.now().isoformat()
    }
    response = client.post("/api/v1/meters/readings", json=overload_reading)
    assert response.status_code == 201

    # 6. Retrieve Alerts (check that overload alert was registered)
    response = client.get("/api/v1/alerts/", headers=headers)
    assert response.status_code == 200
    alerts = response.json()
    assert len(alerts) >= 1
    assert any("MTR-TST-99" in a["message"] for a in alerts)

    # 7. Get grid analytics summary
    response = client.get("/api/v1/analytics/", headers=headers)
    assert response.status_code == 200
    analytics = response.json()
    assert "load_metrics_24h" in analytics
    assert "consumption_kwh" in analytics
    assert analytics["load_metrics_24h"]["peak_load_kw"] >= 185.0

def test_forecasting_flow(client):
    headers = get_auth_headers(client)
    
    # 1. Create Zone and Meter
    zone_data = {
        "name": "Forecasting Zone",
        "description": "Zone for forecasting integration test",
        "capacity_limit_kw": 300.0
    }
    res = client.post("/api/v1/zones/", json=zone_data, headers=headers)
    assert res.status_code == 201
    zone_id = res.json()["id"]
    
    meter_data = {
        "serial_number": "MTR-FCST-01",
        "zone_id": zone_id,
        "status": "active",
        "capacity_limit_kw": 150.0
    }
    res = client.post("/api/v1/meters/", json=meter_data, headers=headers)
    assert res.status_code == 201
    meter_id = res.json()["id"]
    
    # 2. Ingest 30 hours of historical readings to satisfy history requirements (>= 25 readings)
    base_time = datetime(2026, 6, 1, 0, 0, 0)
    for i in range(30):
        reading_time = base_time + timedelta(hours=i)
        reading_data = {
            "meter_id": meter_id,
            "zone_id": zone_id,
            "voltage": 220.0,
            "current": 5.0,
            "power_consumption": 1.1 + (i % 5) * 0.1,  # minor variance
            "frequency": 50.0,
            "temperature": 25.0,
            "timestamp": reading_time.isoformat()
        }
        res = client.post("/api/v1/meters/readings", json=reading_data)
        assert res.status_code == 201

    # 3. Test Meter-level forecasting
    predict_req = {
        "zone_id": zone_id,
        "meter_id": meter_id,
        "horizon_hours": 6
    }
    response = client.post("/api/v1/predict/", json=predict_req, headers=headers)
    assert response.status_code == 200
    pred_data = response.json()
    assert pred_data["zone_id"] == zone_id
    assert pred_data["meter_id"] == meter_id
    assert len(pred_data["predictions"]) == 6
    
    # 4. Test Zone-level forecasting
    predict_req_zone = {
        "zone_id": zone_id,
        "meter_id": None,
        "horizon_hours": 12
    }
    response = client.post("/api/v1/predict/", json=predict_req_zone, headers=headers)
    assert response.status_code == 200
    pred_data_zone = response.json()
    assert pred_data_zone["zone_id"] == zone_id
    assert pred_data_zone["meter_id"] is None
    assert len(pred_data_zone["predictions"]) == 12

    # 5. Test mismatched meter and zone
    predict_req_mismatch = {
        "zone_id": zone_id,
        "meter_id": 9999,  # non-existent meter
        "horizon_hours": 6
    }
    response = client.post("/api/v1/predict/", json=predict_req_mismatch, headers=headers)
    assert response.status_code == 404

