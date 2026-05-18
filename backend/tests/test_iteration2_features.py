"""
Backend API Tests for La Dolorosa - Iteration 2 Features
Tests: Notifications, Duplicate Carrete, Status Filter (active/closed), Archive/Reopen
"""
import pytest
import requests
import os
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL environment variable is required")

# Test session token from iteration 1
TEST_SESSION_TOKEN = "test_session_1776416691489"


@pytest.fixture
def api_client():
    """Shared requests session"""
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture
def auth_client(api_client):
    """Session with auth header"""
    api_client.headers.update({"Authorization": f"Bearer {TEST_SESSION_TOKEN}"})
    return api_client


# ============ NOTIFICATIONS ENDPOINT TESTS ============
class TestNotifications:
    """GET /api/notifications endpoint tests"""

    def test_notifications_returns_pending_count_and_items(self, auth_client):
        """GET /api/notifications should return pending_count and items list"""
        response = auth_client.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        
        # Verify response structure
        assert "pending_count" in data, "Response should have pending_count"
        assert "items" in data, "Response should have items list"
        assert isinstance(data["pending_count"], int), "pending_count should be int"
        assert isinstance(data["items"], list), "items should be list"
        print(f"✓ GET /api/notifications returns pending_count={data['pending_count']}, items={len(data['items'])}")

    def test_notifications_requires_auth(self, api_client):
        """GET /api/notifications without auth should return 401"""
        response = api_client.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ GET /api/notifications requires authentication")

    def test_notifications_with_pending_payment(self, auth_client, api_client):
        """GET /api/notifications should include pending payments"""
        # Create carrete with participant and item
        carrete = auth_client.post(f"{BASE_URL}/api/carretes", 
                                   json={"name": "TEST_Notif_Pending", "tip_percent": 10}).json()
        cid = carrete["id"]
        share_id = carrete["share_id"]
        
        # Add participant
        p = auth_client.post(f"{BASE_URL}/api/carretes/{cid}/participants", 
                             json={"name": "TEST_NotifPayer"}).json()
        pid = p["id"]
        
        # Add item
        auth_client.post(f"{BASE_URL}/api/carretes/{cid}/items", 
                         json={"name": "TEST_Item", "price": 5000, "consumer_ids": [pid]})
        
        # Report payment (public endpoint, no auth)
        api_client.post(f"{BASE_URL}/api/public/carretes/{share_id}/participants/{pid}/pay",
                        json={"participant_id": pid, "amount": 5500, "note": "Test notification"})
        
        # Check notifications
        response = auth_client.get(f"{BASE_URL}/api/notifications")
        assert response.status_code == 200
        data = response.json()
        
        # Find our payment in notifications
        notif = next((n for n in data["items"] if n["carrete_id"] == cid), None)
        assert notif is not None, "Pending payment should appear in notifications"
        assert notif["participant_name"] == "TEST_NotifPayer"
        assert notif["amount"] == 5500
        assert notif["note"] == "Test notification"
        assert "payment_id" in notif
        assert "reported_at" in notif
        
        # Cleanup
        auth_client.delete(f"{BASE_URL}/api/carretes/{cid}")
        print("✓ GET /api/notifications includes pending payments with correct structure")


# ============ DUPLICATE CARRETE TESTS ============
class TestDuplicateCarrete:
    """POST /api/carretes/{id}/duplicate endpoint tests"""

    def test_duplicate_creates_new_carrete(self, auth_client):
        """POST /api/carretes/{id}/duplicate should create new carrete"""
        # Create source carrete
        src = auth_client.post(f"{BASE_URL}/api/carretes", 
                               json={"name": "TEST_Source_Carrete", "tip_percent": 15}).json()
        src_id = src["id"]
        
        # Add participants
        p1 = auth_client.post(f"{BASE_URL}/api/carretes/{src_id}/participants", 
                              json={"name": "TEST_Alice", "is_birthday": True}).json()
        p2 = auth_client.post(f"{BASE_URL}/api/carretes/{src_id}/participants", 
                              json={"name": "TEST_Bob", "is_birthday": False}).json()
        
        # Add items
        auth_client.post(f"{BASE_URL}/api/carretes/{src_id}/items", 
                         json={"name": "TEST_Pizza", "price": 15000, "consumer_ids": [p1["id"], p2["id"]]})
        
        # Report a payment
        api_client = requests.Session()
        api_client.post(f"{BASE_URL}/api/public/carretes/{src['share_id']}/participants/{p1['id']}/pay",
                        json={"participant_id": p1["id"], "amount": 8000})
        
        # Duplicate
        response = auth_client.post(f"{BASE_URL}/api/carretes/{src_id}/duplicate")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        dup = response.json()
        
        # Verify duplicate properties
        assert dup["id"] != src_id, "Duplicate should have new ID"
        assert dup["name"] == "TEST_Source_Carrete (copia)", "Name should have (copia) suffix"
        assert dup["tip_percent"] == 15, "tip_percent should be preserved"
        assert dup["status"] == "active", "Status should be active"
        assert len(dup["participants"]) == 2, "Participants should be copied"
        assert len(dup["items"]) == 0, "Items should be empty"
        assert len(dup["payments"]) == 0, "Payments should be empty"
        
        # Verify participant IDs are new
        src_pids = {p1["id"], p2["id"]}
        dup_pids = {p["id"] for p in dup["participants"]}
        assert src_pids.isdisjoint(dup_pids), "Participant IDs should be new UUIDs"
        
        # Verify participant names preserved
        dup_names = {p["name"] for p in dup["participants"]}
        assert "TEST_Alice" in dup_names
        assert "TEST_Bob" in dup_names
        
        # Verify is_birthday is reset to False
        for p in dup["participants"]:
            assert p["is_birthday"] == False, "is_birthday should be reset to False"
        
        # Cleanup
        auth_client.delete(f"{BASE_URL}/api/carretes/{src_id}")
        auth_client.delete(f"{BASE_URL}/api/carretes/{dup['id']}")
        print("✓ POST /api/carretes/{id}/duplicate creates correct duplicate")

    def test_duplicate_requires_auth(self, auth_client):
        """POST /api/carretes/{id}/duplicate without auth should return 401"""
        # Create carrete
        carrete = auth_client.post(f"{BASE_URL}/api/carretes", 
                                   json={"name": "TEST_Dup_Auth"}).json()
        cid = carrete["id"]
        
        # Try duplicate without auth using fresh session
        no_auth_client = requests.Session()
        no_auth_client.headers.update({"Content-Type": "application/json"})
        response = no_auth_client.post(f"{BASE_URL}/api/carretes/{cid}/duplicate")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        # Cleanup
        auth_client.delete(f"{BASE_URL}/api/carretes/{cid}")
        print("✓ POST /api/carretes/{id}/duplicate requires authentication")

    def test_duplicate_nonexistent_carrete(self, auth_client):
        """POST /api/carretes/{id}/duplicate with invalid ID should return 404"""
        response = auth_client.post(f"{BASE_URL}/api/carretes/nonexistent-id/duplicate")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ POST /api/carretes/{id}/duplicate returns 404 for invalid ID")


# ============ STATUS FILTER TESTS ============
class TestStatusFilter:
    """GET /api/carretes?status= filter tests"""

    def test_filter_active_carretes(self, auth_client):
        """GET /api/carretes?status=active should return only active carretes"""
        # Create active carrete
        active = auth_client.post(f"{BASE_URL}/api/carretes", 
                                  json={"name": "TEST_Active_Filter"}).json()
        
        # Create and close another carrete
        closed = auth_client.post(f"{BASE_URL}/api/carretes", 
                                  json={"name": "TEST_Closed_Filter"}).json()
        auth_client.put(f"{BASE_URL}/api/carretes/{closed['id']}", json={"status": "closed"})
        
        # Filter active
        response = auth_client.get(f"{BASE_URL}/api/carretes?status=active")
        assert response.status_code == 200
        data = response.json()
        
        # Verify only active carretes
        for c in data:
            assert c["status"] != "closed", f"Found closed carrete in active filter: {c['name']}"
        
        # Verify our active carrete is in the list
        active_ids = [c["id"] for c in data]
        assert active["id"] in active_ids, "Active carrete should be in filtered list"
        assert closed["id"] not in active_ids, "Closed carrete should NOT be in active filter"
        
        # Cleanup
        auth_client.delete(f"{BASE_URL}/api/carretes/{active['id']}")
        auth_client.delete(f"{BASE_URL}/api/carretes/{closed['id']}")
        print("✓ GET /api/carretes?status=active returns only active carretes")

    def test_filter_closed_carretes(self, auth_client):
        """GET /api/carretes?status=closed should return only closed carretes"""
        # Create and close a carrete
        carrete = auth_client.post(f"{BASE_URL}/api/carretes", 
                                   json={"name": "TEST_Closed_Only"}).json()
        auth_client.put(f"{BASE_URL}/api/carretes/{carrete['id']}", json={"status": "closed"})
        
        # Filter closed
        response = auth_client.get(f"{BASE_URL}/api/carretes?status=closed")
        assert response.status_code == 200
        data = response.json()
        
        # Verify only closed carretes
        for c in data:
            assert c["status"] == "closed", f"Found non-closed carrete in closed filter: {c['name']}"
        
        # Verify our closed carrete is in the list
        closed_ids = [c["id"] for c in data]
        assert carrete["id"] in closed_ids, "Closed carrete should be in filtered list"
        
        # Cleanup
        auth_client.delete(f"{BASE_URL}/api/carretes/{carrete['id']}")
        print("✓ GET /api/carretes?status=closed returns only closed carretes")

    def test_no_filter_returns_all(self, auth_client):
        """GET /api/carretes without status filter should return all carretes"""
        # Create active and closed carretes
        active = auth_client.post(f"{BASE_URL}/api/carretes", 
                                  json={"name": "TEST_All_Active"}).json()
        closed = auth_client.post(f"{BASE_URL}/api/carretes", 
                                  json={"name": "TEST_All_Closed"}).json()
        auth_client.put(f"{BASE_URL}/api/carretes/{closed['id']}", json={"status": "closed"})
        
        # Get all
        response = auth_client.get(f"{BASE_URL}/api/carretes")
        assert response.status_code == 200
        data = response.json()
        
        all_ids = [c["id"] for c in data]
        assert active["id"] in all_ids, "Active carrete should be in unfiltered list"
        assert closed["id"] in all_ids, "Closed carrete should be in unfiltered list"
        
        # Cleanup
        auth_client.delete(f"{BASE_URL}/api/carretes/{active['id']}")
        auth_client.delete(f"{BASE_URL}/api/carretes/{closed['id']}")
        print("✓ GET /api/carretes without filter returns all carretes")


# ============ ARCHIVE/REOPEN TESTS ============
class TestArchiveReopen:
    """PUT /api/carretes/{id} status change tests"""

    def test_close_carrete(self, auth_client):
        """PUT /api/carretes/{id} with status=closed should archive carrete"""
        carrete = auth_client.post(f"{BASE_URL}/api/carretes", 
                                   json={"name": "TEST_To_Close"}).json()
        cid = carrete["id"]
        assert carrete["status"] == "active"
        
        # Close
        response = auth_client.put(f"{BASE_URL}/api/carretes/{cid}", json={"status": "closed"})
        assert response.status_code == 200
        assert response.json()["status"] == "closed"
        
        # Verify persistence
        get_resp = auth_client.get(f"{BASE_URL}/api/carretes/{cid}")
        assert get_resp.json()["status"] == "closed"
        
        # Cleanup
        auth_client.delete(f"{BASE_URL}/api/carretes/{cid}")
        print("✓ PUT /api/carretes/{id} with status=closed archives carrete")

    def test_reopen_carrete(self, auth_client):
        """PUT /api/carretes/{id} with status=active should reopen carrete"""
        carrete = auth_client.post(f"{BASE_URL}/api/carretes", 
                                   json={"name": "TEST_To_Reopen"}).json()
        cid = carrete["id"]
        
        # Close first
        auth_client.put(f"{BASE_URL}/api/carretes/{cid}", json={"status": "closed"})
        
        # Reopen
        response = auth_client.put(f"{BASE_URL}/api/carretes/{cid}", json={"status": "active"})
        assert response.status_code == 200
        assert response.json()["status"] == "active"
        
        # Verify persistence
        get_resp = auth_client.get(f"{BASE_URL}/api/carretes/{cid}")
        assert get_resp.json()["status"] == "active"
        
        # Cleanup
        auth_client.delete(f"{BASE_URL}/api/carretes/{cid}")
        print("✓ PUT /api/carretes/{id} with status=active reopens carrete")


# ============ CLEANUP ============
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data():
    """Cleanup TEST_ prefixed carretes after all tests"""
    yield
    try:
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {TEST_SESSION_TOKEN}"
        })
        carretes = session.get(f"{BASE_URL}/api/carretes").json()
        for c in carretes:
            if c["name"].startswith("TEST_"):
                session.delete(f"{BASE_URL}/api/carretes/{c['id']}")
        print("✓ Cleaned up TEST_ carretes")
    except Exception as e:
        print(f"Cleanup warning: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
