"""
Backend API Tests for La Dolorosa - Bill Splitting App
Tests: Auth, Profile, Carretes CRUD, Participants, Items, Summary, Public endpoints, Payments, File Upload
"""
import pytest
import requests
import os
from datetime import datetime, timezone, timedelta

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
if not BASE_URL:
    raise ValueError("REACT_APP_BACKEND_URL environment variable is required")

# Test session token created via mongosh
TEST_SESSION_TOKEN = "test_session_1776416691489"
TEST_USER_ID = "test-user-1776416691489"


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


# ============ AUTH TESTS ============
class TestAuth:
    """Authentication endpoint tests"""

    def test_auth_me_without_token(self, api_client):
        """GET /api/auth/me without token should return 401"""
        response = api_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ /api/auth/me returns 401 without token")

    def test_auth_me_with_valid_token(self, auth_client):
        """GET /api/auth/me with valid token should return user"""
        response = auth_client.get(f"{BASE_URL}/api/auth/me")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "user_id" in data
        assert "email" in data
        assert "name" in data
        print(f"✓ /api/auth/me returns user: {data['name']}")

    def test_auth_session_without_session_id(self, api_client):
        """POST /api/auth/session without session_id should return 400"""
        response = api_client.post(f"{BASE_URL}/api/auth/session", json={})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ /api/auth/session returns 400 without session_id")


# ============ PROFILE TESTS ============
class TestProfile:
    """Profile endpoint tests"""

    def test_get_profile(self, auth_client):
        """GET /api/profile should return user profile"""
        response = auth_client.get(f"{BASE_URL}/api/profile")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "user_id" in data
        assert "bank_details" in data or data.get("bank_details") is None
        print(f"✓ GET /api/profile returns profile for {data.get('name')}")

    def test_update_profile_bank_details(self, auth_client):
        """PUT /api/profile should update bank_details"""
        new_bank = f"TEST_BANK_{datetime.now().timestamp()}"
        response = auth_client.put(f"{BASE_URL}/api/profile", json={"bank_details": new_bank})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["bank_details"] == new_bank
        
        # Verify persistence with GET
        get_response = auth_client.get(f"{BASE_URL}/api/profile")
        assert get_response.status_code == 200
        assert get_response.json()["bank_details"] == new_bank
        print(f"✓ PUT /api/profile updates bank_details and persists")


# ============ CARRETES CRUD TESTS ============
class TestCarretes:
    """Carretes CRUD tests"""

    def test_create_carrete(self, auth_client):
        """POST /api/carretes should create a new carrete"""
        payload = {"name": "TEST_Carrete_Create", "tip_percent": 15.0}
        response = auth_client.post(f"{BASE_URL}/api/carretes", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["name"] == payload["name"]
        assert data["tip_percent"] == payload["tip_percent"]
        assert "id" in data
        assert "share_id" in data
        print(f"✓ POST /api/carretes creates carrete: {data['id']}")
        return data["id"]

    def test_list_carretes(self, auth_client):
        """GET /api/carretes should return list of carretes"""
        response = auth_client.get(f"{BASE_URL}/api/carretes")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert isinstance(data, list)
        print(f"✓ GET /api/carretes returns {len(data)} carretes")

    def test_get_carrete_by_id(self, auth_client):
        """GET /api/carretes/{id} should return specific carrete"""
        # First create one
        create_resp = auth_client.post(f"{BASE_URL}/api/carretes", json={"name": "TEST_Get_Carrete"})
        carrete_id = create_resp.json()["id"]
        
        response = auth_client.get(f"{BASE_URL}/api/carretes/{carrete_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["id"] == carrete_id
        print(f"✓ GET /api/carretes/{carrete_id} returns carrete")

    def test_update_carrete_tip_percent(self, auth_client):
        """PUT /api/carretes/{id} should update tip_percent"""
        # Create carrete
        create_resp = auth_client.post(f"{BASE_URL}/api/carretes", json={"name": "TEST_Update_Tip"})
        carrete_id = create_resp.json()["id"]
        
        # Update tip
        response = auth_client.put(f"{BASE_URL}/api/carretes/{carrete_id}", json={"tip_percent": 20.0})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert response.json()["tip_percent"] == 20.0
        
        # Verify persistence
        get_resp = auth_client.get(f"{BASE_URL}/api/carretes/{carrete_id}")
        assert get_resp.json()["tip_percent"] == 20.0
        print(f"✓ PUT /api/carretes/{carrete_id} updates tip_percent")

    def test_delete_carrete(self, auth_client):
        """DELETE /api/carretes/{id} should delete carrete"""
        # Create carrete
        create_resp = auth_client.post(f"{BASE_URL}/api/carretes", json={"name": "TEST_Delete_Carrete"})
        carrete_id = create_resp.json()["id"]
        
        # Delete
        response = auth_client.delete(f"{BASE_URL}/api/carretes/{carrete_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verify deletion
        get_resp = auth_client.get(f"{BASE_URL}/api/carretes/{carrete_id}")
        assert get_resp.status_code == 404
        print(f"✓ DELETE /api/carretes/{carrete_id} removes carrete")


# ============ PARTICIPANTS TESTS ============
class TestParticipants:
    """Participants CRUD tests"""

    @pytest.fixture
    def carrete_with_id(self, auth_client):
        """Create a carrete for participant tests"""
        resp = auth_client.post(f"{BASE_URL}/api/carretes", json={"name": "TEST_Participants_Carrete"})
        return resp.json()["id"]

    def test_add_participant(self, auth_client, carrete_with_id):
        """POST /api/carretes/{id}/participants should add participant"""
        payload = {"name": "TEST_Juan", "is_birthday": False}
        response = auth_client.post(f"{BASE_URL}/api/carretes/{carrete_with_id}/participants", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["name"] == "TEST_Juan"
        assert "id" in data
        print(f"✓ POST participants adds: {data['name']}")
        return data["id"]

    def test_toggle_birthday(self, auth_client, carrete_with_id):
        """PUT /api/carretes/{id}/participants/{pid} should toggle is_birthday"""
        # Add participant
        add_resp = auth_client.post(f"{BASE_URL}/api/carretes/{carrete_with_id}/participants", 
                                    json={"name": "TEST_Birthday_Person", "is_birthday": False})
        pid = add_resp.json()["id"]
        
        # Toggle birthday
        response = auth_client.put(f"{BASE_URL}/api/carretes/{carrete_with_id}/participants/{pid}",
                                   json={"name": "TEST_Birthday_Person", "is_birthday": True})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verify
        carrete = auth_client.get(f"{BASE_URL}/api/carretes/{carrete_with_id}").json()
        participant = next((p for p in carrete["participants"] if p["id"] == pid), None)
        assert participant is not None
        assert participant["is_birthday"] == True
        print(f"✓ PUT participants/{pid} toggles birthday")

    def test_delete_participant(self, auth_client, carrete_with_id):
        """DELETE /api/carretes/{id}/participants/{pid} should remove participant"""
        # Add participant
        add_resp = auth_client.post(f"{BASE_URL}/api/carretes/{carrete_with_id}/participants", 
                                    json={"name": "TEST_ToDelete"})
        pid = add_resp.json()["id"]
        
        # Delete
        response = auth_client.delete(f"{BASE_URL}/api/carretes/{carrete_with_id}/participants/{pid}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verify removal
        carrete = auth_client.get(f"{BASE_URL}/api/carretes/{carrete_with_id}").json()
        assert not any(p["id"] == pid for p in carrete["participants"])
        print(f"✓ DELETE participants/{pid} removes participant")


# ============ ITEMS TESTS ============
class TestItems:
    """Items CRUD tests"""

    @pytest.fixture
    def carrete_with_participants(self, auth_client):
        """Create carrete with participants for item tests"""
        resp = auth_client.post(f"{BASE_URL}/api/carretes", json={"name": "TEST_Items_Carrete"})
        carrete_id = resp.json()["id"]
        
        # Add participants
        p1 = auth_client.post(f"{BASE_URL}/api/carretes/{carrete_id}/participants", 
                              json={"name": "TEST_P1"}).json()
        p2 = auth_client.post(f"{BASE_URL}/api/carretes/{carrete_id}/participants", 
                              json={"name": "TEST_P2"}).json()
        return {"carrete_id": carrete_id, "p1_id": p1["id"], "p2_id": p2["id"]}

    def test_add_item(self, auth_client, carrete_with_participants):
        """POST /api/carretes/{id}/items should add item"""
        cid = carrete_with_participants["carrete_id"]
        p1_id = carrete_with_participants["p1_id"]
        
        payload = {
            "name": "TEST_Pizza",
            "price": 15000,
            "quantity": 1,
            "consumer_ids": [p1_id],
            "is_birthday_item": False
        }
        response = auth_client.post(f"{BASE_URL}/api/carretes/{cid}/items", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["name"] == "TEST_Pizza"
        assert data["price"] == 15000
        print(f"✓ POST items adds: {data['name']}")

    def test_add_birthday_item(self, auth_client, carrete_with_participants):
        """POST /api/carretes/{id}/items with is_birthday_item=True"""
        cid = carrete_with_participants["carrete_id"]
        
        payload = {
            "name": "TEST_Birthday_Cake",
            "price": 20000,
            "quantity": 1,
            "consumer_ids": [],
            "is_birthday_item": True
        }
        response = auth_client.post(f"{BASE_URL}/api/carretes/{cid}/items", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["is_birthday_item"] == True
        print(f"✓ POST items adds birthday item: {data['name']}")

    def test_update_item(self, auth_client, carrete_with_participants):
        """PUT /api/carretes/{id}/items/{item_id} should update item"""
        cid = carrete_with_participants["carrete_id"]
        p1_id = carrete_with_participants["p1_id"]
        
        # Add item
        add_resp = auth_client.post(f"{BASE_URL}/api/carretes/{cid}/items", 
                                    json={"name": "TEST_ToUpdate", "price": 5000, "consumer_ids": [p1_id]})
        item_id = add_resp.json()["id"]
        
        # Update
        response = auth_client.put(f"{BASE_URL}/api/carretes/{cid}/items/{item_id}",
                                   json={"price": 7500})
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verify
        carrete = auth_client.get(f"{BASE_URL}/api/carretes/{cid}").json()
        item = next((i for i in carrete["items"] if i["id"] == item_id), None)
        assert item["price"] == 7500
        print(f"✓ PUT items/{item_id} updates price")

    def test_delete_item(self, auth_client, carrete_with_participants):
        """DELETE /api/carretes/{id}/items/{item_id} should remove item"""
        cid = carrete_with_participants["carrete_id"]
        
        # Add item
        add_resp = auth_client.post(f"{BASE_URL}/api/carretes/{cid}/items", 
                                    json={"name": "TEST_ToDelete", "price": 3000, "consumer_ids": []})
        item_id = add_resp.json()["id"]
        
        # Delete
        response = auth_client.delete(f"{BASE_URL}/api/carretes/{cid}/items/{item_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verify
        carrete = auth_client.get(f"{BASE_URL}/api/carretes/{cid}").json()
        assert not any(i["id"] == item_id for i in carrete["items"])
        print(f"✓ DELETE items/{item_id} removes item")


# ============ SUMMARY TESTS ============
class TestSummary:
    """Summary computation tests"""

    def test_summary_basic(self, auth_client):
        """GET /api/carretes/{id}/summary should compute per-person totals"""
        # Create carrete with 10% tip
        carrete = auth_client.post(f"{BASE_URL}/api/carretes", 
                                   json={"name": "TEST_Summary", "tip_percent": 10}).json()
        cid = carrete["id"]
        
        # Add 2 participants
        p1 = auth_client.post(f"{BASE_URL}/api/carretes/{cid}/participants", 
                              json={"name": "TEST_Alice"}).json()
        p2 = auth_client.post(f"{BASE_URL}/api/carretes/{cid}/participants", 
                              json={"name": "TEST_Bob"}).json()
        
        # Add item shared by both (10000 / 2 = 5000 each)
        auth_client.post(f"{BASE_URL}/api/carretes/{cid}/items", 
                         json={"name": "TEST_Shared", "price": 10000, "consumer_ids": [p1["id"], p2["id"]]})
        
        # Get summary
        response = auth_client.get(f"{BASE_URL}/api/carretes/{cid}/summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        summary = response.json()
        
        assert "per_person" in summary
        assert "grand_total" in summary
        assert summary["tip_percent"] == 10
        
        # Each person: 5000 subtotal + 500 tip = 5500
        for person in summary["per_person"]:
            assert person["subtotal"] == 5000
            assert person["tip"] == 500
            assert person["total"] == 5500
        
        print(f"✓ GET summary computes correctly: grand_total={summary['grand_total']}")

    def test_summary_birthday_item_split(self, auth_client):
        """Birthday items should be split among non-birthday participants"""
        carrete = auth_client.post(f"{BASE_URL}/api/carretes", 
                                   json={"name": "TEST_Birthday_Summary", "tip_percent": 0}).json()
        cid = carrete["id"]
        
        # Add birthday person and 2 others
        bday = auth_client.post(f"{BASE_URL}/api/carretes/{cid}/participants", 
                                json={"name": "TEST_BirthdayPerson", "is_birthday": True}).json()
        p1 = auth_client.post(f"{BASE_URL}/api/carretes/{cid}/participants", 
                              json={"name": "TEST_Friend1"}).json()
        p2 = auth_client.post(f"{BASE_URL}/api/carretes/{cid}/participants", 
                              json={"name": "TEST_Friend2"}).json()
        
        # Add birthday item (10000 split between 2 non-birthday = 5000 each)
        auth_client.post(f"{BASE_URL}/api/carretes/{cid}/items", 
                         json={"name": "TEST_BirthdayCake", "price": 10000, "is_birthday_item": True})
        
        # Get summary
        summary = auth_client.get(f"{BASE_URL}/api/carretes/{cid}/summary").json()
        
        # Birthday person should pay 0
        bday_summary = next(p for p in summary["per_person"] if p["participant_id"] == bday["id"])
        assert bday_summary["total"] == 0, f"Birthday person should pay 0, got {bday_summary['total']}"
        
        # Others should pay 5000 each
        for pid in [p1["id"], p2["id"]]:
            person = next(p for p in summary["per_person"] if p["participant_id"] == pid)
            assert person["total"] == 5000, f"Non-birthday should pay 5000, got {person['total']}"
        
        print(f"✓ Birthday item split correctly among non-birthday participants")


# ============ PUBLIC ENDPOINTS TESTS ============
class TestPublicEndpoints:
    """Public (no auth) endpoint tests"""

    @pytest.fixture
    def public_carrete(self, auth_client):
        """Create carrete with share_id for public tests"""
        carrete = auth_client.post(f"{BASE_URL}/api/carretes", 
                                   json={"name": "TEST_Public_Carrete"}).json()
        cid = carrete["id"]
        share_id = carrete["share_id"]
        
        # Add participant
        p = auth_client.post(f"{BASE_URL}/api/carretes/{cid}/participants", 
                             json={"name": "TEST_PublicPerson"}).json()
        
        # Add item
        auth_client.post(f"{BASE_URL}/api/carretes/{cid}/items", 
                         json={"name": "TEST_Item", "price": 5000, "consumer_ids": [p["id"]]})
        
        return {"carrete_id": cid, "share_id": share_id, "participant_id": p["id"]}

    def test_public_get_carrete(self, api_client, public_carrete):
        """GET /api/public/carretes/{share_id} should return carrete without auth"""
        share_id = public_carrete["share_id"]
        response = api_client.get(f"{BASE_URL}/api/public/carretes/{share_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "carrete_name" in data
        assert "summary" in data
        assert "captain_bank_details" in data
        print(f"✓ GET /api/public/carretes/{share_id} works without auth")

    def test_public_get_participant_bill(self, api_client, public_carrete):
        """GET /api/public/carretes/{share_id}/participants/{pid} should return bill"""
        share_id = public_carrete["share_id"]
        pid = public_carrete["participant_id"]
        
        response = api_client.get(f"{BASE_URL}/api/public/carretes/{share_id}/participants/{pid}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "bill" in data
        assert data["bill"]["participant_id"] == pid
        print(f"✓ GET public participant bill works")

    def test_public_report_payment(self, api_client, public_carrete):
        """POST /api/public/carretes/{share_id}/participants/{pid}/pay should report payment"""
        share_id = public_carrete["share_id"]
        pid = public_carrete["participant_id"]
        
        payload = {
            "participant_id": pid,
            "amount": 5500,
            "screenshot_path": None,
            "note": "TEST_Payment"
        }
        response = api_client.post(f"{BASE_URL}/api/public/carretes/{share_id}/participants/{pid}/pay", 
                                   json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["status"] == "pending"
        assert data["amount"] == 5500
        print(f"✓ POST public payment report works")


# ============ PAYMENT VALIDATION TESTS ============
class TestPaymentValidation:
    """Payment validation tests (captain validates payments)"""

    def test_validate_payment(self, auth_client):
        """PUT /api/carretes/{id}/payments/{payment_id}/validate should update status"""
        # Create carrete with participant and item
        carrete = auth_client.post(f"{BASE_URL}/api/carretes", 
                                   json={"name": "TEST_Validate_Payment"}).json()
        cid = carrete["id"]
        share_id = carrete["share_id"]
        
        p = auth_client.post(f"{BASE_URL}/api/carretes/{cid}/participants", 
                             json={"name": "TEST_Payer"}).json()
        auth_client.post(f"{BASE_URL}/api/carretes/{cid}/items", 
                         json={"name": "TEST_Item", "price": 5000, "consumer_ids": [p["id"]]})
        
        # Report payment (public endpoint, no auth)
        requests.post(f"{BASE_URL}/api/public/carretes/{share_id}/participants/{p['id']}/pay",
                      json={"participant_id": p["id"], "amount": 5500})
        
        # Get payment ID
        carrete_data = auth_client.get(f"{BASE_URL}/api/carretes/{cid}").json()
        payment = carrete_data["payments"][0]
        payment_id = payment["id"]
        
        # Validate payment
        response = auth_client.put(f"{BASE_URL}/api/carretes/{cid}/payments/{payment_id}/validate?status=validated")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Verify status changed
        carrete_data = auth_client.get(f"{BASE_URL}/api/carretes/{cid}").json()
        payment = next(p for p in carrete_data["payments"] if p["id"] == payment_id)
        assert payment["status"] == "validated"
        print(f"✓ PUT validate payment works")


# ============ FILE UPLOAD TESTS ============
class TestFileUpload:
    """File upload/download tests"""

    def test_upload_image(self):
        """POST /api/upload should upload image to object storage"""
        import base64
        # Create a simple test image (1x1 pixel PNG)
        png_1x1 = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        
        # Use requests directly without Content-Type header (let requests set multipart boundary)
        files = {"file": ("test.png", png_1x1, "image/png")}
        response = requests.post(f"{BASE_URL}/api/upload", files=files)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert "file_id" in data
        assert "storage_path" in data
        print(f"✓ POST /api/upload works: file_id={data['file_id']}")
        return data["file_id"]

    def test_get_file(self):
        """GET /api/files/{file_id} should return uploaded file"""
        import base64
        # First upload
        png_1x1 = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        files = {"file": ("test.png", png_1x1, "image/png")}
        upload_resp = requests.post(f"{BASE_URL}/api/upload", files=files)
        assert upload_resp.status_code == 200, f"Upload failed: {upload_resp.text}"
        file_id = upload_resp.json()["file_id"]
        
        # Get file
        response = requests.get(f"{BASE_URL}/api/files/{file_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        assert len(response.content) > 0
        print(f"✓ GET /api/files/{file_id} returns file content")


# ============ CLEANUP ============
@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data():
    """Cleanup TEST_ prefixed carretes after all tests"""
    yield
    # Cleanup after tests
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
