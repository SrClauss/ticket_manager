from motor.motor_asyncio import AsyncIOMotorClient
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
import os


class Settings(BaseSettings):
    mongodb_url: str = "mongodb://admin:password@localhost:27017"
    database_name: str = "ticket_manager"
    
    # Ler variáveis de ambiente do arquivo `.env` (se existir)
    # e ignorar entradas extras para evitar erros quando outras
    # variáveis (JWT, ADMIN, etc.) estiverem presentes no .env
    model_config = ConfigDict(env_file=".env", extra="ignore")


settings = Settings()

# Global variable to store database client
mongodb_client: AsyncIOMotorClient = None
database = None


async def connect_to_mongo():
    """Connect to MongoDB"""
    global mongodb_client, database
    mongodb_client = AsyncIOMotorClient(settings.mongodb_url)
    database = mongodb_client[settings.database_name]
    print(f"Conectado ao MongoDB: {settings.database_name}")


async def close_mongo_connection():
    """Close MongoDB connection"""
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        print("Conexão com MongoDB fechada")


def get_database():
    """Get database instance"""
    return database
