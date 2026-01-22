from fastapi import FastAPI, Request, HTTPException, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.config.database import connect_to_mongo, close_mongo_connection, get_database
from app.config.indexes import create_indexes
from app.config.auth import create_initial_admin
from app.routers import admin, bilheteria, portaria, leads, admin_web, operational_web, admin_management
from app.routers import inscricao
from bson import ObjectId

app = FastAPI(
    title="EventMaster API",
    description="Sistema de gerenciamento de eventos com controle de acesso e emissão de ingressos",
    version="1.0.0"
)

templates = Jinja2Templates(directory="app/templates")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique os domínios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Event handlers for database connection
@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()
    await create_indexes()
    await create_initial_admin()

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()

# Include routers
app.include_router(admin_web.router, prefix="/admin", tags=["Admin Web UI"])
app.include_router(operational_web.router, tags=["Operational Web UI"])
app.include_router(admin.router, prefix="/api/admin", tags=["Administrativo"])
app.include_router(admin_management.router, prefix="/api/admin", tags=["Gerenciamento de Administradores"])
app.include_router(bilheteria.router, prefix="/api/bilheteria", tags=["Bilheteria"])
app.include_router(portaria.router, prefix="/api/portaria", tags=["Portaria/Controle de Acesso"])
app.include_router(leads.router, prefix="/api/leads", tags=["Coletor de Leads"])
# Public inscription routes by event slug/name
app.include_router(inscricao.router, prefix="/inscricao", tags=["Inscricao Publica"]) 
app.include_router(inscricao.router, prefix="/api/inscricao", tags=["Inscricao API"]) 
# Evento API (rendering ingressos)
from app.routers import evento_api
app.include_router(evento_api.router, prefix="/api/eventos", tags=["Eventos API"])
# Planilha upload and import routes (admin)
from app.routers import planilha
app.include_router(planilha.router, prefix="/api/admin", tags=["Planilhas"]) 

@app.get("/ingresso/{ingresso_id}", response_class=HTMLResponse)
async def ingresso_page(request: Request, ingresso_id: str):
    db = get_database()
    try:
        ingresso = await db.ingressos_emitidos.find_one({"_id": ObjectId(ingresso_id)})
    except Exception:
        ingresso = await db.ingressos_emitidos.find_one({"_id": ingresso_id})
    if not ingresso:
        raise HTTPException(status_code=404, detail="Ingresso não encontrado")
    evento_id = ingresso.get("evento_id")
    return templates.TemplateResponse("ingresso_view.html", {"request": request, "evento_id": evento_id, "ingresso_id": str(ingresso.get("_id"))})


@app.get("/")
async def root():
    return {
        "message": "Bem-vindo ao EventMaster API",
        "description": "Sistema de gerenciamento de eventos com controle de acesso",
        "docs": "/docs",
        "redoc": "/redoc",
        "modules": {
            "admin": "/api/admin (Requer X-Admin-Key header)",
            "bilheteria": "/api/bilheteria (Requer X-Token-Bilheteria header)",
            "portaria": "/api/portaria (Requer X-Token-Portaria header)",
            "leads": "/api/leads (Público para coleta)"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "EventMaster API"}

