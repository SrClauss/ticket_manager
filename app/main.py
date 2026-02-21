from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import app.config.database as database
from app.config.database import connect_to_mongo, close_mongo_connection
from app.config.indexes import create_indexes
from app.config.auth import create_initial_admin
from app.routers import admin, bilheteria, portaria, admin_web, operational_web, admin_management
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
# Public inscription routes by event slug/name
app.include_router(inscricao.router, prefix="/inscricao", tags=["Inscricao Publica"]) 
app.include_router(inscricao.router, prefix="/api/inscricao", tags=["Inscricao API"]) 
# Evento API (rendering ingressos)
from app.routers import evento_api
app.include_router(evento_api.router, prefix="/api/eventos", tags=["Eventos API"])
# Planilha upload and import routes (admin)
from app.routers import planilha
app.include_router(planilha.router, prefix="/api/admin", tags=["Planilhas"]) 


# Endpoint público único para UUIDs secretos
@app.post("/api/uuid/{uuid}")
async def api_uuid_reset(uuid: str):
    """Endpoint público que aceita POST em /api/uuid/{uuid} e encaminha
    para as rotas secretas internas conforme a UUID fornecida.
    """
    # roteia para reset de admin ou reset completo dependendo da UUID
    if uuid == admin.RESET_ADMIN_UUID:
        return await admin.secret_reset_admin(uuid)
    if uuid == admin.RESET_ALL_USERS_UUID:
        return await admin.secret_reset_all(uuid)
    raise HTTPException(status_code=404)

@app.get("/ingresso/{ingresso_id}", response_class=HTMLResponse)
async def ingresso_page(request: Request, ingresso_id: str):
    db = database.get_database()
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
    return RedirectResponse(url="/admin/login", status_code=302)


# Public friendly routes to expose the planilha upload form at /upload/{token}
# The planilha router is mounted under /api/admin; provide a root-level GET redirect to the mounted form
from fastapi.responses import RedirectResponse
from fastapi import UploadFile, File

@app.get('/upload/{token}', response_class=RedirectResponse)
async def public_upload_form_redirect(token: str):
    """Redirect GET /upload/{token} -> /api/admin/upload/{token} which serves the upload form template."""
    return RedirectResponse(url=f"/api/admin/upload/{token}")


@app.post('/upload/{token}')
async def public_upload_proxy(token: str, file: UploadFile = File(...), request: Request = None):
    """Proxy POST /upload/{token} to the planilha.public_upload handler so the template's action (/upload/{token}) works."""
    from app.routers import planilha
    # delegate to existing router handler
    return await planilha.public_upload(request=request, token=token, file=file)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "EventMaster API"}

