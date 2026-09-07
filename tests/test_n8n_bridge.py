"""Integration tests for n8n Bridge FastAPI Server."""

import pytest
from fastapi.testclient import TestClient
from src.n8n_bridge.server import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_compile_endpoint():
    payload = {
        "prompt": "Find used furniture in all groups with furniture in name, output in CSV with columns: GroupName | Requires joining (true/false) | post link | date of publish | description snippet (up to 40 words)"
    }
    response = client.post("/compile", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "target" in data
    assert data["target"]["type"] == "group_search"
    assert data["output_config"]["format"] == "csv"


def test_synthesize_endpoint():
    payload = {
        "posts": [
            {
                "post_id": "p1",
                "group_name": "Furniture TLV",
                "author_name": "Adam",
                "published_iso": "2025-02-10T12:00:00",
                "content_text": "Looking to buy dining chairs",
                "snippet": "Looking to buy dining chairs",
                "post_url": "https://facebook.com/p1",
                "requires_joining": False,
            }
        ],
        "group_records": [
            {
                "group_name": "Private Furniture VIP",
                "group_url": "https://facebook.com/groups/vip",
                "requires_joining": True,
                "is_accessible": False,
            }
        ],
        "format": "csv",
        "columns": [
            "GroupName",
            "Requires joining (true/false)",
            "post link",
            "date of publish",
            "description snippet (up to 40 words)",
        ],
    }
    response = client.post("/synthesize", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert "formatted_output" in res_data
    assert "Furniture TLV,false,https://facebook.com/p1" in res_data["formatted_output"]
    assert "Private Furniture VIP,true" in res_data["formatted_output"]
