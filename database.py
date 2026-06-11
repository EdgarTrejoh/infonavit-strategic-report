import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()
logger = logging.getLogger(__name__)

DATABASE_URL_ENV = os.getenv("DATABASE_URL")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "infonavit")

if DATABASE_URL_ENV is None and os.getenv("DB_PASSWORD") is None:
    logger.warning(
        "DB_PASSWORD no configurado; se usara el default local de desarrollo. "
        "En produccion use Secret Manager o una variable segura."
    )

# String de conexión para PostgreSQL usando psycopg2
DATABASE_URL = DATABASE_URL_ENV or f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Crear el motor de conexión
try:
    engine = create_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
except Exception as e:
    logger.warning("Error al inicializar el motor de base de datos: %s", type(e).__name__)
    engine = None

def health_check():
    """Valida disponibilidad de PostgreSQL sin exponer credenciales."""
    if engine is None:
        return False, "No se pudo conectar a PostgreSQL. Verifica host, puerto, base y credenciales."

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "Conexion PostgreSQL disponible."
    except Exception as e:
        logger.warning("Health check PostgreSQL fallido: %s", type(e).__name__)
        return False, "No se pudo conectar a PostgreSQL. Verifica host, puerto, base y credenciales."

def get_db():
    """Generador para manejar la sesión de la base de datos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
