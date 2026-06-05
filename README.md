# La Dolorosa 🍻

Aplicacion para dividir cuentas en restoranes y bares, con OCR de boletas via Gemini 2.5 Flash.

## URLs de Produccion

| Servicio | URL |
|---|---|
| **Frontend** | https://dolorosa.misdeseos.cl |
| **Backend API** | https://api-dolorosa.misdeseos.cl |

## Arquitectura

```
dolorosaapk/
├── backend/          # FastAPI + MongoDB
│   ├── server.py
│   ├── requirements.txt
│   ├── Dockerfile                 # Para CapRover app: dolorosa-backend
│   └── captain-definition
├── frontend/         # React + Tailwind CSS
│   ├── src/
│   ├── Dockerfile                 # Para CapRover app: dolorosa-frontend
│   ├── nginx.conf
│   └── captain-definition
├── Dockerfile.frontend            # Deploy frontend desde raiz del repo
└── captain-definition             # Apunta a Dockerfile.frontend (raiz)
```

## Despliegue en CapRover

### Backend — app: `dolorosa-backend`
- **Subdirectory**: `backend`
- **Variables de entorno** (configurar en CapRover → App Configs):

| Variable | Valor |
|---|---|
| `MONGO_URL` | `mongodb://user:pass@host:27017` |
| `DB_NAME` | `la_dolorosa` |
| `GEMINI_API_KEY` | Tu API Key de Google AI Studio |
| `CORS_ORIGINS` | `https://dolorosa.misdeseos.cl` |
| `FRONTEND_URL` | `https://dolorosa.misdeseos.cl` |
| `GOOGLE_CLIENT_ID` | (opcional) Para login con Google |
| `GOOGLE_CLIENT_SECRET` | (opcional) Para login con Google |
| `GOOGLE_REDIRECT_URI` | `https://api-dolorosa.misdeseos.cl/api/auth/google/callback` |

### Frontend — app: `dolorosa-frontend`
- **Subdirectory**: `frontend`
- **Build Arguments** (configurar en CapRover → App Configs → Build Args):

| Variable | Valor |
|---|---|
| `REACT_APP_BACKEND_URL` | `https://api-dolorosa.misdeseos.cl` |

### Deploy via CLI

```bash
# Instalar CLI de CapRover
npm install -g caprover

# Login
caprover login

# Deploy backend
cd backend
caprover deploy --appName dolorosa-backend

# Deploy frontend
cd ../frontend
caprover deploy --appName dolorosa-frontend
```

## Obtener API Key de Gemini

1. Ve a https://aistudio.google.com/apikey
2. Crea una nueva API Key (gratis)
3. Copia la key y pegala en CapRover como `GEMINI_API_KEY`

## Desarrollo local

```bash
# Backend
cd backend
cp .env.example .env   # editar con tus valores
pip install -r requirements.txt
uvicorn server:app --reload --port 8000

# Frontend
cd frontend
echo 'REACT_APP_BACKEND_URL=http://localhost:8000' > .env
npm install --legacy-peer-deps
npm start
```
