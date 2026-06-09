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

# String de conexión para PostgreSQL usando psycopg2
DATABASE_URL = DATABASE_URL_ENV or f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Crear el motor de conexión
try:
    engine = create_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
except Exception as e:
    logger.warning("Error al inicializar el motor de base de datos: %s", e)
    engine = None

def health_check():
    """Valida disponibilidad de PostgreSQL sin exponer credenciales."""
    if engine is None:
        return False, "No se pudo inicializar el motor de base de datos."

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "Conexion PostgreSQL disponible."
    except Exception as e:
        return False, f"No se pudo conectar a PostgreSQL: {e}"

def get_db():
    """Generador para manejar la sesión de la base de datos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
