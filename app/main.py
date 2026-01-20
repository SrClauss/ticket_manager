from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.database import connect_to_mongo, close_mongo_connection
from app.routers import tickets

app = FastAPI(
    title="Ticket Manager API",
    description="Sistema de gerenciamento de tickets usando FastAPI e MongoDB",
    version="1.0.0"
)

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

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()

# Include routers
app.include_router(tickets.router, prefix="/api/tickets", tags=["tickets"])

@app.get("/")
async def root():
    return {
        "message": "Bem-vindo ao Ticket Manager API",
        "docs": "/docs",
        "redoc": "/redoc"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
