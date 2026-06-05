# La Dolorosa 🍻

Aplicacion para dividir cuentas en restoranes y bares, con OCR de boletas via GPT-4o.

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

### Opcion A: Deploy de cada app por separado (recomendado)

1. **Backend** — En CapRover crea la app `dolorosa-backend`, conecta el repo y configura:
   - **Subdirectory**: `backend`
   - **Variables de entorno**:
     - `MONGO_URL` — URL de conexion a MongoDB
     - `DB_NAME` — Nombre de la base de datos (ej: `la_dolorosa`)
     - `EMERGENT_LLM_KEY` — API Key de Emergent para OCR
     - `CORS_ORIGINS` — URL del frontend (ej: `https://dolorosa.tudominio.com`)

2. **Frontend** — En CapRover crea la app `dolorosa-frontend`, conecta el repo y configura:
   - **Subdirectory**: `frontend`
   - **Build Arguments**:
     - `REACT_APP_BACKEND_URL` — URL del backend (ej: `https://api.tudominio.com`)

### Opcion B: Deploy del frontend desde la raiz

Usa el `captain-definition` de la raiz del repo que apunta a `Dockerfile.frontend`.
Configura el Build Argument `REACT_APP_BACKEND_URL` en CapRover.

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

## Variables de Entorno requeridas

### Backend
| Variable | Descripcion | Ejemplo |
|---|---|---|
| `MONGO_URL` | URI de MongoDB | `mongodb://user:pass@host:27017` |
| `DB_NAME` | Nombre de la DB | `la_dolorosa` |
| `EMERGENT_LLM_KEY` | API Key Emergent | `sk-...` |
| `CORS_ORIGINS` | URLs permitidas (separadas por coma) | `https://dolorosa.tudominio.com` |

### Frontend (Build Arguments)
| Variable | Descripcion | Ejemplo |
|---|---|---|
| `REACT_APP_BACKEND_URL` | URL base del backend | `https://api.tudominio.com` |

## Desarrollo local

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn server:app --reload --port 8000

# Frontend
cd frontend
npm install --legacy-peer-deps
npm start
```
