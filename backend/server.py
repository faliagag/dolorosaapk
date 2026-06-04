from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, UploadFile, File, Header, Query, Cookie
from fastapi.responses import Response as FastAPIResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import uuid
import json
import base64
import re
import secrets
import bcrypt
import requests
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone, timedelta

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Object storage
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
APP_NAME = "la-dolorosa"
storage_key_cache = {"key": None}

def init_storage():
    if storage_key_cache["key"]:
        return storage_key_cache["key"]
    try:
        resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
        resp.raise_for_status()
        storage_key_cache["key"] = resp.json()["storage_key"]
        return storage_key_cache["key"]
    except Exception as e:
        logging.error(f"Storage init failed: {e}")
        return None

def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    if not key:
        raise HTTPException(status_code=500, detail="Storage not initialized")
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120,
    )
    resp.raise_for_status()
    return resp.json()

def get_object(path: str):
    key = init_storage()
    if not key:
        raise HTTPException(status_code=500, detail="Storage not initialized")
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

app = FastAPI()
api_router = APIRouter(prefix="/api")

# ---------- Models ----------
class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    bank_details: Optional[str] = ""
    created_at: Optional[str] = None

class Participant(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    is_birthday: bool = False

class Item(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    price: float
    quantity: int = 1
    consumer_ids: List[str] = []  # participant IDs who consumed it
    is_birthday_item: bool = False  # if True, gets split among non-birthday participants

class Payment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    participant_id: str
    amount: float
    screenshot_path: Optional[str] = None
    status: str = "pending"  # pending, validated, rejected
    reported_at: str
    note: Optional[str] = ""

class Carrete(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    share_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:10])
    tip_percent: float = 10.0
    participants: List[Participant] = []
    items: List[Item] = []
    payments: List[Payment] = []
    status: str = "active"  # active, closed
    created_at: str

class CarreteCreate(BaseModel):
    name: str
    tip_percent: float = 10.0

class ParticipantCreate(BaseModel):
    name: str
    is_birthday: bool = False

class ItemCreate(BaseModel):
    name: str
    price: float
    quantity: int = 1
    consumer_ids: List[str] = []
    is_birthday_item: bool = False

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None
    consumer_ids: Optional[List[str]] = None
    is_birthday_item: Optional[bool] = None

class ProfileUpdate(BaseModel):
    bank_details: Optional[str] = None
    name: Optional[str] = None

class CarreteUpdate(BaseModel):
    name: Optional[str] = None
    tip_percent: Optional[float] = None
    status: Optional[str] = None

class PaymentReport(BaseModel):
    participant_id: str
    amount: float
    screenshot_path: Optional[str] = None
    note: Optional[str] = ""

# ---------- Auth helpers ----------
async def get_user_from_token(session_token: Optional[str]):
    if not session_token:
        return None
    session = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
    if not session:
        return None
    expires_at = session.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0, "password_hash": 0})
    return user

async def require_user(request: Request):
    cookie_token = request.cookies.get("session_token")
    auth_header = request.headers.get("authorization", "")
    header_token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else None
    token = cookie_token or header_token
    user = await get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

# ---------- Password helpers ----------
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

async def _create_session(user_id: str, response: Response) -> str:
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )
    return session_token

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str

class LoginRequest(BaseModel):
    email: str
    password: str

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# ---------- Auth routes ----------
@api_router.post("/auth/session")
async def auth_session(request: Request, response: Response):
    body = await request.json()
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    try:
        resp = requests.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Session exchange failed: {e}")

    email = data["email"]
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": data.get("name", existing.get("name")), "picture": data.get("picture", existing.get("picture"))}},
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "email": email,
            "name": data.get("name", ""),
            "picture": data.get("picture", ""),
            "bank_details": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    session_token = data["session_token"]
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return user

@api_router.get("/auth/me")
async def auth_me(request: Request):
    user = await require_user(request)
    return user

@api_router.post("/auth/register")
async def auth_register(body: RegisterRequest, response: Response):
    email = body.email.strip().lower()
    name = body.name.strip()
    password = body.password

    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Email inválido")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")
    if not name or len(name) < 2:
        raise HTTPException(status_code=400, detail="Nombre demasiado corto")

    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese email")

    user_id = f"user_{uuid.uuid4().hex[:12]}"
    await db.users.insert_one({
        "user_id": user_id,
        "email": email,
        "name": name,
        "picture": "",
        "bank_details": "",
        "password_hash": hash_password(password),
        "auth_provider": "password",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await _create_session(user_id, response)
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    return user

@api_router.post("/auth/login")
async def auth_login(body: LoginRequest, response: Response):
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Email inválido")

    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")
    if not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

    await _create_session(user["user_id"], response)
    user.pop("password_hash", None)
    return user

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    password: str

@api_router.post("/auth/forgot-password")
async def auth_forgot_password(body: ForgotPasswordRequest, request: Request):
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Email inválido")

    user = await db.users.find_one({"email": email}, {"_id": 0})
    # Always return success shape to prevent email enumeration.
    # In dev mode (no email service), return the reset_link so the
    # frontend can display it to the user.
    if not user or not user.get("password_hash"):
        return {"ok": True, "reset_link": None, "dev_mode": True}

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    await db.password_reset_tokens.insert_one({
        "token": token,
        "user_id": user["user_id"],
        "email": email,
        "expires_at": expires_at.isoformat(),
        "used": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    # Build link using the frontend origin so it works for both dev & preview
    origin = request.headers.get("origin") or request.headers.get("referer", "").split("/")[0:3]
    if isinstance(origin, list):
        origin = "/".join(origin).rstrip("/")
    reset_link = f"{origin}/reset-password?token={token}"

    logging.info(f"[forgot-password] reset link for {email}: {reset_link}")
    return {"ok": True, "reset_link": reset_link, "dev_mode": True}

@api_router.post("/auth/reset-password")
async def auth_reset_password(body: ResetPasswordRequest, response: Response):
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")

    record = await db.password_reset_tokens.find_one({"token": body.token}, {"_id": 0})
    if not record or record.get("used"):
        raise HTTPException(status_code=400, detail="Link inválido o ya usado")

    expires_at = record.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Link expirado, solicita uno nuevo")

    new_hash = hash_password(body.password)
    await db.users.update_one(
        {"user_id": record["user_id"]},
        {"$set": {"password_hash": new_hash}},
    )
    await db.password_reset_tokens.update_one(
        {"token": body.token},
        {"$set": {"used": True, "used_at": datetime.now(timezone.utc).isoformat()}},
    )
    # Invalidate existing sessions for security
    await db.user_sessions.delete_many({"user_id": record["user_id"]})
    # Create fresh session
    await _create_session(record["user_id"], response)
    user = await db.users.find_one({"user_id": record["user_id"]}, {"_id": 0, "password_hash": 0})
    return user

@api_router.post("/auth/logout")
async def auth_logout(request: Request, response: Response):
    token = request.cookies.get("session_token")
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/")
    return {"ok": True}

# ---------- Profile ----------
@api_router.get("/profile")
async def get_profile(request: Request):
    user = await require_user(request)
    return user

@api_router.put("/profile")
async def update_profile(body: ProfileUpdate, request: Request):
    user = await require_user(request)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": updates})
    return await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0})

# ---------- Carretes ----------
def _serialize_carrete(c):
    # Remove _id if present
    c.pop("_id", None)
    return c

@api_router.post("/carretes")
async def create_carrete(body: CarreteCreate, request: Request):
    user = await require_user(request)
    carrete = Carrete(
        user_id=user["user_id"],
        name=body.name,
        tip_percent=body.tip_percent,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    doc = carrete.model_dump()
    await db.carretes.insert_one(doc.copy())
    return _serialize_carrete(doc)

@api_router.get("/carretes")
async def list_carretes(request: Request, status: Optional[str] = Query(None)):
    user = await require_user(request)
    query = {"user_id": user["user_id"]}
    if status:
        query["status"] = status
    carretes = await db.carretes.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return carretes

@api_router.post("/carretes/{carrete_id}/duplicate")
async def duplicate_carrete(carrete_id: str, request: Request):
    user = await require_user(request)
    src = await db.carretes.find_one({"id": carrete_id, "user_id": user["user_id"]}, {"_id": 0})
    if not src:
        raise HTTPException(status_code=404, detail="Not found")
    new_participants = [
        {"id": str(uuid.uuid4()), "name": p["name"], "is_birthday": False}
        for p in src.get("participants", [])
    ]
    new_carrete = Carrete(
        user_id=user["user_id"],
        name=f"{src['name']} (copia)",
        tip_percent=src.get("tip_percent", 10.0),
        participants=[Participant(**p) for p in new_participants],
        items=[],
        payments=[],
        status="active",
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    doc = new_carrete.model_dump()
    await db.carretes.insert_one(doc.copy())
    return _serialize_carrete(doc)

@api_router.get("/notifications")
async def get_notifications(request: Request):
    user = await require_user(request)
    carretes = await db.carretes.find(
        {"user_id": user["user_id"], "payments.status": "pending"},
        {"_id": 0},
    ).to_list(1000)
    items = []
    for c in carretes:
        p_by_id = {p["id"]: p for p in c.get("participants", [])}
        for pay in c.get("payments", []):
            if pay.get("status") == "pending":
                person = p_by_id.get(pay["participant_id"], {})
                items.append({
                    "carrete_id": c["id"],
                    "carrete_name": c["name"],
                    "payment_id": pay["id"],
                    "participant_id": pay["participant_id"],
                    "participant_name": person.get("name", "—"),
                    "amount": pay.get("amount", 0),
                    "reported_at": pay.get("reported_at"),
                    "note": pay.get("note", ""),
                })
    items.sort(key=lambda x: x.get("reported_at") or "", reverse=True)
    return {"pending_count": len(items), "items": items}

@api_router.get("/carretes/{carrete_id}")
async def get_carrete(carrete_id: str, request: Request):
    user = await require_user(request)
    c = await db.carretes.find_one({"id": carrete_id, "user_id": user["user_id"]}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    return c

@api_router.put("/carretes/{carrete_id}")
async def update_carrete(carrete_id: str, body: CarreteUpdate, request: Request):
    user = await require_user(request)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        await db.carretes.update_one(
            {"id": carrete_id, "user_id": user["user_id"]},
            {"$set": updates},
        )
    c = await db.carretes.find_one({"id": carrete_id, "user_id": user["user_id"]}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    return c

@api_router.delete("/carretes/{carrete_id}")
async def delete_carrete(carrete_id: str, request: Request):
    user = await require_user(request)
    await db.carretes.delete_one({"id": carrete_id, "user_id": user["user_id"]})
    return {"ok": True}

# ---------- Participants ----------
@api_router.post("/carretes/{carrete_id}/participants")
async def add_participant(carrete_id: str, body: ParticipantCreate, request: Request):
    user = await require_user(request)
    p = Participant(name=body.name, is_birthday=body.is_birthday)
    await db.carretes.update_one(
        {"id": carrete_id, "user_id": user["user_id"]},
        {"$push": {"participants": p.model_dump()}},
    )
    return p

@api_router.put("/carretes/{carrete_id}/participants/{pid}")
async def update_participant(carrete_id: str, pid: str, body: ParticipantCreate, request: Request):
    user = await require_user(request)
    await db.carretes.update_one(
        {"id": carrete_id, "user_id": user["user_id"], "participants.id": pid},
        {"$set": {"participants.$.name": body.name, "participants.$.is_birthday": body.is_birthday}},
    )
    c = await db.carretes.find_one({"id": carrete_id, "user_id": user["user_id"]}, {"_id": 0})
    return c

@api_router.delete("/carretes/{carrete_id}/participants/{pid}")
async def delete_participant(carrete_id: str, pid: str, request: Request):
    user = await require_user(request)
    await db.carretes.update_one(
        {"id": carrete_id, "user_id": user["user_id"]},
        {"$pull": {"participants": {"id": pid}}},
    )
    # Remove from consumer_ids in items
    await db.carretes.update_one(
        {"id": carrete_id, "user_id": user["user_id"]},
        {"$pull": {"items.$[].consumer_ids": pid}},
    )
    return {"ok": True}

# ---------- Items ----------
@api_router.post("/carretes/{carrete_id}/items")
async def add_item(carrete_id: str, body: ItemCreate, request: Request):
    user = await require_user(request)
    item = Item(**body.model_dump())
    await db.carretes.update_one(
        {"id": carrete_id, "user_id": user["user_id"]},
        {"$push": {"items": item.model_dump()}},
    )
    return item

@api_router.put("/carretes/{carrete_id}/items/{item_id}")
async def update_item(carrete_id: str, item_id: str, body: ItemUpdate, request: Request):
    user = await require_user(request)
    updates = {f"items.$.{k}": v for k, v in body.model_dump().items() if v is not None}
    if updates:
        await db.carretes.update_one(
            {"id": carrete_id, "user_id": user["user_id"], "items.id": item_id},
            {"$set": updates},
        )
    c = await db.carretes.find_one({"id": carrete_id, "user_id": user["user_id"]}, {"_id": 0})
    return c

@api_router.delete("/carretes/{carrete_id}/items/{item_id}")
async def delete_item(carrete_id: str, item_id: str, request: Request):
    user = await require_user(request)
    await db.carretes.update_one(
        {"id": carrete_id, "user_id": user["user_id"]},
        {"$pull": {"items": {"id": item_id}}},
    )
    return {"ok": True}

# ---------- Summary computation ----------
def compute_summary(carrete: dict):
    participants = carrete.get("participants", [])
    items = carrete.get("items", [])
    tip_percent = carrete.get("tip_percent", 0.0)
    non_birthday_ids = [p["id"] for p in participants if not p.get("is_birthday")]
    birthday_ids = {p["id"] for p in participants if p.get("is_birthday")}

    totals = {p["id"]: {"subtotal": 0.0, "items": []} for p in participants}
    grand_subtotal = 0.0

    for item in items:
        item_total = float(item["price"]) * int(item.get("quantity", 1))
        grand_subtotal += item_total
        is_bday = item.get("is_birthday_item", False)
        consumers = item.get("consumer_ids", [])

        if is_bday:
            # Explicitly a birthday gift item: split among non-birthday
            targets = non_birthday_ids if non_birthday_ids else [p["id"] for p in participants]
            if not targets:
                continue
            share = item_total / len(targets)
            for pid in targets:
                if pid in totals:
                    totals[pid]["subtotal"] += share
                    totals[pid]["items"].append({
                        "item_id": item["id"],
                        "name": item["name"] + " 🎂",
                        "amount": round(share, 2),
                        "shared_with": len(targets),
                    })
        else:
            if not consumers:
                # If nobody assigned, split among all
                consumers = [p["id"] for p in participants]
            # Exclude birthday participants from paying (they go free)
            consumers_effective = [c for c in consumers if c not in birthday_ids]
            if not consumers_effective:
                # Only birthday people consumed → redistribute to all non-birthday
                consumers_effective = non_birthday_ids or list(consumers)
            if not consumers_effective:
                continue
            share = item_total / len(consumers_effective)
            for pid in consumers_effective:
                if pid in totals:
                    totals[pid]["subtotal"] += share
                    totals[pid]["items"].append({
                        "item_id": item["id"],
                        "name": item["name"],
                        "amount": round(share, 2),
                        "shared_with": len(consumers_effective),
                    })

    # Add tip
    result = []
    grand_total = 0.0
    for p in participants:
        pid = p["id"]
        sub = totals[pid]["subtotal"]
        tip = sub * (tip_percent / 100.0)
        total = sub + tip
        grand_total += total
        result.append({
            "participant_id": pid,
            "participant_name": p["name"],
            "is_birthday": p.get("is_birthday", False),
            "subtotal": round(sub, 2),
            "tip": round(tip, 2),
            "total": round(total, 2),
            "items": totals[pid]["items"],
        })

    return {
        "per_person": result,
        "grand_subtotal": round(grand_subtotal, 2),
        "grand_tip": round(grand_subtotal * (tip_percent / 100.0), 2),
        "grand_total": round(grand_total, 2),
        "tip_percent": tip_percent,
    }

@api_router.get("/carretes/{carrete_id}/summary")
async def carrete_summary(carrete_id: str, request: Request):
    user = await require_user(request)
    c = await db.carretes.find_one({"id": carrete_id, "user_id": user["user_id"]}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    return compute_summary(c)

# ---------- Public ----------
@api_router.get("/public/carretes/{share_id}")
async def public_get_carrete(share_id: str):
    c = await db.carretes.find_one({"share_id": share_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    owner = await db.users.find_one({"user_id": c["user_id"]}, {"_id": 0})
    summary = compute_summary(c)
    return {
        "carrete_id": c["id"],
        "carrete_name": c["name"],
        "share_id": c["share_id"],
        "captain_name": owner["name"] if owner else "",
        "captain_bank_details": owner.get("bank_details", "") if owner else "",
        "participants": c.get("participants", []),
        "summary": summary,
        "payments": [
            {k: v for k, v in p.items() if k != "screenshot_path"}
            for p in c.get("payments", [])
        ],
    }

@api_router.get("/public/carretes/{share_id}/participants/{pid}")
async def public_get_participant_bill(share_id: str, pid: str):
    c = await db.carretes.find_one({"share_id": share_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    summary = compute_summary(c)
    person = next((p for p in summary["per_person"] if p["participant_id"] == pid), None)
    if not person:
        raise HTTPException(status_code=404, detail="Participant not found")
    owner = await db.users.find_one({"user_id": c["user_id"]}, {"_id": 0})
    payment = next((p for p in c.get("payments", []) if p["participant_id"] == pid), None)
    return {
        "carrete_name": c["name"],
        "share_id": c["share_id"],
        "captain_name": owner["name"] if owner else "",
        "captain_bank_details": owner.get("bank_details", "") if owner else "",
        "bill": person,
        "payment": {k: v for k, v in payment.items() if k != "screenshot_path"} if payment else None,
        "tip_percent": c.get("tip_percent", 0.0),
    }

@api_router.post("/public/carretes/{share_id}/participants/{pid}/pay")
async def public_report_payment(share_id: str, pid: str, body: PaymentReport):
    c = await db.carretes.find_one({"share_id": share_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    # Remove any existing payment for this participant
    await db.carretes.update_one(
        {"share_id": share_id},
        {"$pull": {"payments": {"participant_id": pid}}},
    )
    payment = Payment(
        participant_id=pid,
        amount=body.amount,
        screenshot_path=body.screenshot_path,
        note=body.note or "",
        reported_at=datetime.now(timezone.utc).isoformat(),
        status="pending",
    )
    await db.carretes.update_one(
        {"share_id": share_id},
        {"$push": {"payments": payment.model_dump()}},
    )
    return payment

@api_router.put("/carretes/{carrete_id}/payments/{payment_id}/validate")
async def validate_payment(carrete_id: str, payment_id: str, status: str = Query("validated"), request: Request = None):
    user = await require_user(request)
    await db.carretes.update_one(
        {"id": carrete_id, "user_id": user["user_id"], "payments.id": payment_id},
        {"$set": {"payments.$.status": status}},
    )
    c = await db.carretes.find_one({"id": carrete_id, "user_id": user["user_id"]}, {"_id": 0})
    return c

# ---------- File Upload / Download (public for sharing) ----------
@api_router.post("/upload")
async def upload(file: UploadFile = File(...)):
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files allowed")
    ext = file.filename.split(".")[-1] if "." in (file.filename or "") else "jpg"
    file_id = str(uuid.uuid4())
    path = f"{APP_NAME}/screenshots/{file_id}.{ext}"
    data = await file.read()
    result = put_object(path, data, file.content_type or "image/jpeg")
    await db.files.insert_one({
        "id": file_id,
        "storage_path": result["path"],
        "original_filename": file.filename,
        "content_type": file.content_type,
        "size": result.get("size"),
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"file_id": file_id, "storage_path": result["path"]}

@api_router.get("/files/{file_id}")
async def get_file(file_id: str):
    record = await db.files.find_one({"id": file_id, "is_deleted": False}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    data, content_type = get_object(record["storage_path"])
    return FastAPIResponse(content=data, media_type=record.get("content_type") or content_type)

# ---------- OCR with Gemini Vision ----------
@api_router.post("/ocr/scan")
async def ocr_scan(request: Request, file: UploadFile = File(...)):
    await require_user(request)
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files allowed")
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini key not configured")

    raw = await file.read()
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large (max 8MB)")

    b64 = base64.b64encode(raw).decode("utf-8")

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"emergentintegrations not available: {e}")

    system = (
        "Eres un experto extrayendo datos de boletas y recibos de restaurantes, bares y comercios. "
        "Extraes SOLO los ítems consumidos (no subtotales, propinas, impuestos, ni totales). "
        "Respondes EXCLUSIVAMENTE JSON válido sin texto adicional, sin comillas markdown."
    )
    prompt = (
        "Extrae los ítems de esta boleta. Devuelve un JSON con la forma exacta:\n"
        '{"items": [{"name": "nombre del ítem", "price": 0, "quantity": 1}]}\n\n'
        "Reglas:\n"
        "- price debe ser el precio TOTAL de la línea (cantidad × unidad) como número entero en la moneda local "
        "(remueve puntos y comas de miles, p.ej. '21.000' → 21000, '9.500' → 9500).\n"
        "- quantity es la cantidad que aparece al inicio de la línea (o 1 si no hay).\n"
        "- IGNORA: subtotal, total, propina, tip, IVA, neto, impuestos, cambio, vuelto, servicio, mesa, ID, fecha, "
        "garzón, RUT, folio, dirección, teléfono, logos, 'pre-cuenta', encabezados.\n"
        '- Si no hay ítems claros, devuelve {"items": []}.\n'
        "- No agregues explicaciones. SOLO el JSON."
    )

    chat = LlmChat(
        api_key=os.environ["GEMINI_API_KEY"],
        session_id=f"ocr-{uuid.uuid4().hex[:8]}",
        system_message=system,
    ).with_model("google", "gemini-2.5-flash")

    msg = UserMessage(
        text=prompt,
        file_contents=[ImageContent(image_base64=b64)],
    )

    try:
        response = await chat.send_message(msg)
    except Exception as e:
        logging.error(f"OCR LLM call failed: {e}")
        raise HTTPException(status_code=502, detail=f"OCR failed: {e}")

    # Extract JSON from response (strip potential markdown)
    text = (response or "").strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        text = m.group(0)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logging.error(f"OCR response not valid JSON: {response!r}")
        return {"items": []}

    raw_items = parsed.get("items", []) if isinstance(parsed, dict) else []
    clean = []
    for it in raw_items:
        if not isinstance(it, dict):
            continue
        name = str(it.get("name", "")).strip()
        try:
            price = float(it.get("price", 0))
        except (TypeError, ValueError):
            continue
        try:
            qty = int(it.get("quantity", 1) or 1)
        except (TypeError, ValueError):
            qty = 1
        if not name or price <= 0:
            continue
        clean.append({"name": name[:60], "price": round(price), "quantity": max(1, qty)})
    return {"items": clean}

# ---------- Startup ----------
@app.on_event("startup")
async def startup():
    try:
        init_storage()
        logging.info("Storage initialized")
    except Exception as e:
        logging.error(f"Storage init failed: {e}")
    try:
        await db.users.create_index("email", unique=True)
        await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=3600)
        await db.password_reset_tokens.create_index("token", unique=True)
        logging.info("Indexes ensured")
    except Exception as e:
        logging.error(f"Index creation failed: {e}")

@app.on_event("shutdown")
async def shutdown():
    client.close()

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@api_router.get("/health")
async def health_check():
    return {"status": "ok"}
