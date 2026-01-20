from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config.database import connect_to_mongo, close_mongo_connection
from app.config.indexes import create_indexes
from app.config.auth import create_initial_admin
from app.routers import admin, bilheteria, portaria, leads, admin_web, operational_web, admin_management

app = FastAPI(
    title="EventMaster API",
    description="Sistema de gerenciamento de eventos com controle de acesso e emissão de ingressos",
    version="1.0.0"
)

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

