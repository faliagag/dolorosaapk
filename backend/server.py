from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, UploadFile, File, Query
from fastapi.responses import Response as FastAPIResponse, RedirectResponse
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
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from requests_oauthlib import OAuth2Session
import requests

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MongoDB
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Google OAuth config
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', '')
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://dolorosa.misdeseos.cl')

GOOGLE_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

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
    consumer_ids: List[str] = []
    is_birthday_item: bool = False

class Payment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    participant_id: str
    amount: float
    screenshot_path: Optional[str] = None
    status: str = "pending"
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
    status: str = "active"
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

class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str

class LoginRequest(BaseModel):
    email: str
    password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    password: str

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

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
    return await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0, "password_hash": 0})

async def require_user(request: Request):
    cookie_token = request.cookies.get("session_token")
    auth_header = request.headers.get("authorization", "")
    header_token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else None
    user = await get_user_from_token(cookie_token or header_token)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

# ---------- Password helpers ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False

async def _create_session(user_id: str, response: Response) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    response.set_cookie(
        key="session_token", value=token,
        max_age=7 * 24 * 3600, httponly=True, secure=True, samesite="none", path="/",
    )
    return token

# ---------- Google OAuth ----------
@api_router.get("/auth/google")
async def auth_google_redirect():
    if not GOOGLE_CLIENT_ID or not GOOGLE_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Google OAuth no configurado")
    oauth = OAuth2Session(GOOGLE_CLIENT_ID, redirect_uri=GOOGLE_REDIRECT_URI, scope=["openid", "email", "profile"])
    url, state = oauth.authorization_url(GOOGLE_AUTH_URL, access_type="offline", prompt="select_account")
    resp = RedirectResponse(url=url)
    resp.set_cookie("oauth_state", state, httponly=True, secure=True, samesite="none", max_age=600)
    return resp

@api_router.get("/auth/google/callback")
async def auth_google_callback(request: Request, response: Response):
    code = request.query_params.get("code")
    saved_state = request.cookies.get("oauth_state", "")
    if not code:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=no_code")
    try:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "0"
        oauth = OAuth2Session(GOOGLE_CLIENT_ID, redirect_uri=GOOGLE_REDIRECT_URI, state=saved_state)
        oauth.fetch_token(GOOGLE_TOKEN_URL, code=code, client_secret=GOOGLE_CLIENT_SECRET)
    except Exception as e:
        logger.error(f"Google token exchange failed: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=token_failed")
    try:
        userinfo = oauth.get(GOOGLE_USERINFO_URL).json()
    except Exception as e:
        logger.error(f"Google userinfo failed: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=userinfo_failed")
    email = userinfo.get("email", "").lower()
    if not email:
        return RedirectResponse(url=f"{FRONTEND_URL}/login?error=no_email")
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one({"user_id": user_id}, {"$set": {
            "name": userinfo.get("name", existing.get("name", "")),
            "picture": userinfo.get("picture", existing.get("picture", "")),
        }})
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id, "email": email,
            "name": userinfo.get("name", ""), "picture": userinfo.get("picture", ""),
            "bank_details": "", "auth_provider": "google",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    session_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one({
        "user_id": user_id, "session_token": session_token,
        "expires_at": expires_at.isoformat(), "created_at": datetime.now(timezone.utc).isoformat(),
    })
    redirect = RedirectResponse(url=f"{FRONTEND_URL}/dashboard")
    redirect.set_cookie(key="session_token", value=session_token, max_age=7*24*3600,
                        httponly=True, secure=True, samesite="none", path="/")
    redirect.delete_cookie("oauth_state")
    return redirect

# ---------- Auth routes ----------
@api_router.get("/auth/me")
async def auth_me(request: Request):
    return await require_user(request)

@api_router.post("/auth/register")
async def auth_register(body: RegisterRequest, response: Response):
    email = body.email.strip().lower()
    name = body.name.strip()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Email inv\u00e1lido")
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="La contrase\u00f1a debe tener al menos 6 caracteres")
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Nombre demasiado corto")
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese email")
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    await db.users.insert_one({
        "user_id": user_id, "email": email, "name": name,
        "picture": "", "bank_details": "",
        "password_hash": hash_password(body.password),
        "auth_provider": "password",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    await _create_session(user_id, response)
    return await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})

@api_router.post("/auth/login")
async def auth_login(body: LoginRequest, response: Response):
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Email inv\u00e1lido")
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or not user.get("password_hash") or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Email o contrase\u00f1a incorrectos")
    await _create_session(user["user_id"], response)
    user.pop("password_hash", None)
    return user

@api_router.post("/auth/forgot-password")
async def auth_forgot_password(body: ForgotPasswordRequest):
    email = body.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Email inv\u00e1lido")
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or not user.get("password_hash"):
        return {"ok": True, "reset_link": None}
    token = secrets.token_urlsafe(32)
    await db.password_reset_tokens.insert_one({
        "token": token, "user_id": user["user_id"], "email": email,
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "used": False, "created_at": datetime.now(timezone.utc).isoformat(),
    })
    reset_link = f"{FRONTEND_URL}/reset-password?token={token}"
    logger.info(f"[forgot-password] reset link for {email}: {reset_link}")
    return {"ok": True, "reset_link": reset_link}

@api_router.post("/auth/reset-password")
async def auth_reset_password(body: ResetPasswordRequest, response: Response):
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="La contrase\u00f1a debe tener al menos 6 caracteres")
    record = await db.password_reset_tokens.find_one({"token": body.token}, {"_id": 0})
    if not record or record.get("used"):
        raise HTTPException(status_code=400, detail="Link inv\u00e1lido o ya usado")
    expires_at = datetime.fromisoformat(record["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Link expirado")
    await db.users.update_one({"user_id": record["user_id"]}, {"$set": {"password_hash": hash_password(body.password)}})
    await db.password_reset_tokens.update_one({"token": body.token}, {"$set": {"used": True}})
    await db.user_sessions.delete_many({"user_id": record["user_id"]})
    await _create_session(record["user_id"], response)
    return await db.users.find_one({"user_id": record["user_id"]}, {"_id": 0, "password_hash": 0})

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
    return await require_user(request)

@api_router.put("/profile")
async def update_profile(body: ProfileUpdate, request: Request):
    user = await require_user(request)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if updates:
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": updates})
    return await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "password_hash": 0})

# ---------- Carretes ----------
def _serialize(c):
    c.pop("_id", None)
    return c

@api_router.post("/carretes")
async def create_carrete(body: CarreteCreate, request: Request):
    user = await require_user(request)
    doc = Carrete(user_id=user["user_id"], name=body.name, tip_percent=body.tip_percent,
                  created_at=datetime.now(timezone.utc).isoformat()).model_dump()
    await db.carretes.insert_one(doc.copy())
    return _serialize(doc)

@api_router.get("/carretes")
async def list_carretes(request: Request, status: Optional[str] = Query(None)):
    user = await require_user(request)
    q = {"user_id": user["user_id"]}
    if status:
        q["status"] = status
    return await db.carretes.find(q, {"_id": 0}).sort("created_at", -1).to_list(1000)

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
        await db.carretes.update_one({"id": carrete_id, "user_id": user["user_id"]}, {"$set": updates})
    c = await db.carretes.find_one({"id": carrete_id, "user_id": user["user_id"]}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    return c

@api_router.delete("/carretes/{carrete_id}")
async def delete_carrete(carrete_id: str, request: Request):
    user = await require_user(request)
    await db.carretes.delete_one({"id": carrete_id, "user_id": user["user_id"]})
    return {"ok": True}

@api_router.post("/carretes/{carrete_id}/duplicate")
async def duplicate_carrete(carrete_id: str, request: Request):
    user = await require_user(request)
    src = await db.carretes.find_one({"id": carrete_id, "user_id": user["user_id"]}, {"_id": 0})
    if not src:
        raise HTTPException(status_code=404, detail="Not found")
    new_p = [{"id": str(uuid.uuid4()), "name": p["name"], "is_birthday": False} for p in src.get("participants", [])]
    doc = Carrete(
        user_id=user["user_id"], name=f"{src['name']} (copia)",
        tip_percent=src.get("tip_percent", 10.0),
        participants=[Participant(**p) for p in new_p],
        created_at=datetime.now(timezone.utc).isoformat(),
    ).model_dump()
    await db.carretes.insert_one(doc.copy())
    return _serialize(doc)

# ---------- Participants ----------
@api_router.post("/carretes/{carrete_id}/participants")
async def add_participant(carrete_id: str, body: ParticipantCreate, request: Request):
    user = await require_user(request)
    p = Participant(name=body.name, is_birthday=body.is_birthday)
    await db.carretes.update_one({"id": carrete_id, "user_id": user["user_id"]}, {"$push": {"participants": p.model_dump()}})
    return p

@api_router.put("/carretes/{carrete_id}/participants/{pid}")
async def update_participant(carrete_id: str, pid: str, body: ParticipantCreate, request: Request):
    user = await require_user(request)
    await db.carretes.update_one(
        {"id": carrete_id, "user_id": user["user_id"], "participants.id": pid},
        {"$set": {"participants.$.name": body.name, "participants.$.is_birthday": body.is_birthday}},
    )
    return await db.carretes.find_one({"id": carrete_id, "user_id": user["user_id"]}, {"_id": 0})

@api_router.delete("/carretes/{carrete_id}/participants/{pid}")
async def delete_participant(carrete_id: str, pid: str, request: Request):
    user = await require_user(request)
    await db.carretes.update_one({"id": carrete_id, "user_id": user["user_id"]}, {"$pull": {"participants": {"id": pid}}})
    await db.carretes.update_one({"id": carrete_id, "user_id": user["user_id"]}, {"$pull": {"items.$[].consumer_ids": pid}})
    return {"ok": True}

# ---------- Items ----------
@api_router.post("/carretes/{carrete_id}/items")
async def add_item(carrete_id: str, body: ItemCreate, request: Request):
    user = await require_user(request)
    item = Item(**body.model_dump())
    await db.carretes.update_one({"id": carrete_id, "user_id": user["user_id"]}, {"$push": {"items": item.model_dump()}})
    return item

@api_router.put("/carretes/{carrete_id}/items/{item_id}")
async def update_item(carrete_id: str, item_id: str, body: ItemUpdate, request: Request):
    user = await require_user(request)
    updates = {f"items.$.{k}": v for k, v in body.model_dump().items() if v is not None}
    if updates:
        await db.carretes.update_one({"id": carrete_id, "user_id": user["user_id"], "items.id": item_id}, {"$set": updates})
    return await db.carretes.find_one({"id": carrete_id, "user_id": user["user_id"]}, {"_id": 0})

@api_router.delete("/carretes/{carrete_id}/items/{item_id}")
async def delete_item(carrete_id: str, item_id: str, request: Request):
    user = await require_user(request)
    await db.carretes.update_one({"id": carrete_id, "user_id": user["user_id"]}, {"$pull": {"items": {"id": item_id}}})
    return {"ok": True}

# ---------- Summary ----------
def compute_summary(carrete: dict):
    participants = carrete.get("participants", [])
    items = carrete.get("items", [])
    tip_pct = carrete.get("tip_percent", 0.0)
    non_bday = [p["id"] for p in participants if not p.get("is_birthday")]
    bday_ids = {p["id"] for p in participants if p.get("is_birthday")}
    totals = {p["id"]: {"subtotal": 0.0, "items": []} for p in participants}
    grand_sub = 0.0
    for item in items:
        total = float(item["price"]) * int(item.get("quantity", 1))
        grand_sub += total
        is_bday = item.get("is_birthday_item", False)
        consumers = item.get("consumer_ids", [])
        if is_bday:
            targets = non_bday if non_bday else [p["id"] for p in participants]
            if not targets:
                continue
            share = total / len(targets)
            for pid in targets:
                if pid in totals:
                    totals[pid]["subtotal"] += share
                    totals[pid]["items"].append({"item_id": item["id"], "name": item["name"] + " \U0001f382", "amount": round(share, 2), "shared_with": len(targets)})
        else:
            if not consumers:
                consumers = [p["id"] for p in participants]
            eff = [c for c in consumers if c not in bday_ids] or non_bday or list(consumers)
            if not eff:
                continue
            share = total / len(eff)
            for pid in eff:
                if pid in totals:
                    totals[pid]["subtotal"] += share
                    totals[pid]["items"].append({"item_id": item["id"], "name": item["name"], "amount": round(share, 2), "shared_with": len(eff)})
    result = []
    grand_total = 0.0
    for p in participants:
        sub = totals[p["id"]]["subtotal"]
        tip = sub * (tip_pct / 100.0)
        total = sub + tip
        grand_total += total
        result.append({"participant_id": p["id"], "participant_name": p["name"], "is_birthday": p.get("is_birthday", False),
                        "subtotal": round(sub, 2), "tip": round(tip, 2), "total": round(total, 2), "items": totals[p["id"]]["items"]})
    return {"per_person": result, "grand_subtotal": round(grand_sub, 2),
            "grand_tip": round(grand_sub * (tip_pct / 100.0), 2), "grand_total": round(grand_total, 2), "tip_percent": tip_pct}

@api_router.get("/carretes/{carrete_id}/summary")
async def carrete_summary(carrete_id: str, request: Request):
    user = await require_user(request)
    c = await db.carretes.find_one({"id": carrete_id, "user_id": user["user_id"]}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    return compute_summary(c)

# ---------- Notifications ----------
@api_router.get("/notifications")
async def get_notifications(request: Request):
    user = await require_user(request)
    carretes = await db.carretes.find({"user_id": user["user_id"], "payments.status": "pending"}, {"_id": 0}).to_list(1000)
    items = []
    for c in carretes:
        p_by_id = {p["id"]: p for p in c.get("participants", [])}
        for pay in c.get("payments", []):
            if pay.get("status") == "pending":
                person = p_by_id.get(pay["participant_id"], {})
                items.append({"carrete_id": c["id"], "carrete_name": c["name"], "payment_id": pay["id"],
                               "participant_id": pay["participant_id"], "participant_name": person.get("name", "\u2014"),
                               "amount": pay.get("amount", 0), "reported_at": pay.get("reported_at"), "note": pay.get("note", "")})
    items.sort(key=lambda x: x.get("reported_at") or "", reverse=True)
    return {"pending_count": len(items), "items": items}

# ---------- Public routes ----------
@api_router.get("/public/carretes/{share_id}")
async def public_get_carrete(share_id: str):
    c = await db.carretes.find_one({"share_id": share_id}, {"_id": 0})
    if not c:
        raise HTTPException(status_code=404, detail="Not found")
    owner = await db.users.find_one({"user_id": c["user_id"]}, {"_id": 0})
    return {
        "carrete_id": c["id"], "carrete_name": c["name"], "share_id": c["share_id"],
        "captain_name": owner["name"] if owner else "",
        "captain_bank_details": owner.get("bank_details", "") if owner else "",
        "participants": c.get("participants", []),
        "summary": compute_summary(c),
        "payments": [{k: v for k, v in p.items() if k != "screenshot_path"} for p in c.get("payments", [])],
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
        "carrete_name": c["name"], "share_id": c["share_id"],
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
    await db.carretes.update_one({"share_id": share_id}, {"$pull": {"payments": {"participant_id": pid}}})
    payment = Payment(participant_id=pid, amount=body.amount, screenshot_path=body.screenshot_path,
                      note=body.note or "", reported_at=datetime.now(timezone.utc).isoformat(), status="pending")
    await db.carretes.update_one({"share_id": share_id}, {"$push": {"payments": payment.model_dump()}})
    return payment

@api_router.put("/carretes/{carrete_id}/payments/{payment_id}/validate")
async def validate_payment(carrete_id: str, payment_id: str, status: str = Query("validated"), request: Request = None):
    user = await require_user(request)
    await db.carretes.update_one(
        {"id": carrete_id, "user_id": user["user_id"], "payments.id": payment_id},
        {"$set": {"payments.$.status": status}},
    )
    return await db.carretes.find_one({"id": carrete_id, "user_id": user["user_id"]}, {"_id": 0})

# ---------- OCR con google-generativeai ----------
@api_router.post("/ocr/scan")
async def ocr_scan(request: Request, file: UploadFile = File(...)):
    await require_user(request)
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files allowed")
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY no configurado")
    raw = await file.read()
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Imagen demasiado grande (max 8MB)")
    try:
        import google.generativeai as genai
        from google.generativeai.types import HarmCategory, HarmBlockThreshold
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-2.0-flash")
        prompt = (
            "Extrae los \u00edtems de esta boleta. Devuelve SOLO un JSON v\u00e1lido con la forma:\n"
            '{"items": [{"name": "nombre", "price": 0, "quantity": 1}]}\n'
            "- price = precio total de la l\u00ednea como n\u00famero entero (ej: '21.000' -> 21000)\n"
            "- IGNORA: subtotal, total, propina, IVA, impuestos, encabezados\n"
            "- Si no hay \u00edtems, devuelve {\"items\": []}\n"
            "- Responde SOLO el JSON, sin markdown ni texto extra."
        )
        img_part = {"mime_type": file.content_type, "data": base64.b64encode(raw).decode()}
        result = model.generate_content(
            [prompt, img_part],
            safety_settings={c: HarmBlockThreshold.BLOCK_NONE for c in HarmCategory if c != HarmCategory.HARM_CATEGORY_UNSPECIFIED},
        )
        text = (result.text or "").strip()
    except Exception as e:
        logger.error(f"OCR Gemini failed: {e}")
        raise HTTPException(status_code=502, detail=f"OCR fallido: {e}")
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        text = m.group(0)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.error(f"OCR response not JSON: {text!r}")
        return {"items": []}
    clean = []
    for it in (parsed.get("items", []) if isinstance(parsed, dict) else []):
        if not isinstance(it, dict):
            continue
        name = str(it.get("name", "")).strip()
        try:
            price = float(it.get("price", 0))
        except (TypeError, ValueError):
            continue
        try:
            qty = max(1, int(it.get("quantity", 1) or 1))
        except (TypeError, ValueError):
            qty = 1
        if name and price > 0:
            clean.append({"name": name[:60], "price": round(price), "quantity": qty})
    return {"items": clean}

# ---------- Health ----------
@api_router.get("/health")
async def health():
    return {"status": "ok"}

# ---------- Startup / Shutdown ----------
@app.on_event("startup")
async def startup():
    try:
        await db.users.create_index("email", unique=True)
        await db.user_sessions.create_index("session_token", unique=True)
        await db.user_sessions.create_index("expires_at", expireAfterSeconds=0)
        await db.password_reset_tokens.create_index("token", unique=True)
        await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=3600)
        logger.info("MongoDB indexes ensured")
    except Exception as e:
        logger.error(f"Index creation failed: {e}")

@app.on_event("shutdown")
async def shutdown():
    client.close()

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "https://dolorosa.misdeseos.cl").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
