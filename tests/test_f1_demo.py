import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.f1_service import f1_service


@pytest.fixture(autouse=True)
def reset_service():
    """Ensure service starts from a clean reset before every test."""
    f1_service.reset_dataset()
    yield
    f1_service.reset_dataset()


client = TestClient(app)


def test_f1_drivers_list():
    response = client.get("/api/f1/drivers")
    assert response.status_code == 200
    drivers = response.json()
    assert len(drivers) == 5
    driver_ids = [d["driver_id"] for d in drivers]
    assert "F1-001" in driver_ids  # Lewis Hamilton
    assert "F1-002" in driver_ids  # Michael Schumacher
    assert "F1-003" in driver_ids  # Max Verstappen
    assert "F1-004" in driver_ids  # Sebastian Vettel
    assert "F1-005" in driver_ids  # Ayrton Senna


def test_f1_driver_details():
    response = client.get("/api/f1/drivers/F1-001")
    assert response.status_code == 200
    data = response.json()
    assert data["driver_name"] == "Lewis Hamilton"
    assert data["working_facts"]["team_for_2020_title"] == "Mercedes"
    assert data["working_facts"]["car_for_2008_title"] == "McLaren MP4-23"
    assert len(data["available_qa_pairs"]) > 0


def test_f1_driver_not_found():
    response = client.get("/api/f1/drivers/NON_EXISTENT")
    assert response.status_code == 404


def test_f1_query_active_fact():
    # Ask about Hamilton's 2020 championship team
    payload = {
        "question": "Which team did Lewis Hamilton win the 2020 Drivers' Championship with?",
        "driver_id": "F1-001",
    }
    response = client.post("/api/f1/ask", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["success"] is True
    assert res["found"] is True
    assert res["is_unlearned"] is False
    assert res["target_attribute"] == "team_for_2020_title"
    assert "Mercedes" in res["answer"]


def test_f1_fact_unlearning_and_verification_cycle():
    # 1. Ask initial question -> Verified present
    ask_before = client.post(
        "/api/f1/ask",
        json={
            "question": "Which team did Lewis Hamilton win the 2020 Drivers' Championship with?",
            "driver_id": "F1-001",
        },
    ).json()
    assert ask_before["found"] is True
    assert "Mercedes" in ask_before["answer"]

    # 2. Forget specific fact 'team_for_2020_title'
    forget_resp = client.post(
        "/api/f1/forget",
        json={"driver_id": "F1-001", "attribute": "team_for_2020_title"},
    )
    assert forget_resp.status_code == 200
    forget_data = forget_resp.json()
    assert forget_data["success"] is True
    assert forget_data["attribute"] == "team_for_2020_title"
    assert forget_data["previous_value"] == "Mercedes"

    # 3. Re-ask exact question -> Must report unlearned / unavailable
    ask_after = client.post(
        "/api/f1/ask",
        json={
            "question": "Which team did Lewis Hamilton win the 2020 Drivers' Championship with?",
            "driver_id": "F1-001",
        },
    ).json()
    assert ask_after["found"] is False
    assert ask_after["is_unlearned"] is True
    assert "unlearned" in ask_after["answer"].lower() or "purged" in ask_after["answer"].lower()

    # 4. Verify retained fact on same driver remains 100% intact
    retention_resp = client.post(
        "/api/f1/verify-retention",
        json={"driver_id": "F1-001", "check_attribute": "car_for_2008_title"},
    )
    assert retention_resp.status_code == 200
    ret_data = retention_resp.json()
    assert ret_data["retained"] is True
    assert ret_data["current_value"] == "McLaren MP4-23"

    # 5. Verify immutable original remains untouched
    details = client.get("/api/f1/drivers/F1-001").json()
    assert details["original_facts"]["team_for_2020_title"] == "Mercedes"
    assert "team_for_2020_title" not in details["working_facts"]
    assert "team_for_2020_title" in details["unlearned_attributes"]


def test_f1_forget_invalid_driver_or_attribute():
    # Invalid driver
    res1 = client.post("/api/f1/forget", json={"driver_id": "UNKNOWN", "attribute": "championship_years"})
    assert res1.status_code == 404

    # Invalid attribute
    res2 = client.post("/api/f1/forget", json={"driver_id": "F1-001", "attribute": "invalid_attribute_xyz"})
    assert res2.status_code == 404


def test_f1_reset_restores_store():
    # Forget Hamilton's 2020 team
    client.post("/api/f1/forget", json={"driver_id": "F1-001", "attribute": "team_for_2020_title"})

    # Check unlearned
    details = client.get("/api/f1/drivers/F1-001").json()
    assert "team_for_2020_title" in details["unlearned_attributes"]

    # Trigger reset
    reset_resp = client.post("/api/f1/reset")
    assert reset_resp.status_code == 200
    assert reset_resp.json()["status"] == "SUCCESS"

    # Verify restored
    details_after = client.get("/api/f1/drivers/F1-001").json()
    assert len(details_after["unlearned_attributes"]) == 0
    assert details_after["working_facts"]["team_for_2020_title"] == "Mercedes"

    # Re-query
    ask_restored = client.post(
        "/api/f1/ask",
        json={
            "question": "Which team did Lewis Hamilton win the 2020 Drivers' Championship with?",
            "driver_id": "F1-001",
        },
    ).json()
    assert ask_restored["found"] is True
    assert "Mercedes" in ask_restored["answer"]


def test_f1_audit_timeline():
    # Execute a query and a forgetting action
    client.post(
        "/api/f1/ask",
        json={"question": "In which years did Max Verstappen win the Drivers' World Championship?", "driver_id": "F1-003"},
    )
    client.post("/api/f1/forget", json={"driver_id": "F1-003", "attribute": "car_for_2021_title"})

    resp = client.get("/api/f1/timeline")
    assert resp.status_code == 200
    timeline = resp.json()
    assert len(timeline) >= 2
    actions = [e["action"] for e in timeline]
    assert "FORGET_FACT" in actions
    assert "QUERY_FACT" in actions

