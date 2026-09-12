from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from pydantic_settings import BaseSettings
from pathlib import Path
from urllib.parse import quote_plus


class Settings(BaseSettings):
    POSTGRES_DB: str = "hospital_management_system"
    POSTGRES_USER: str = "hms_admin"
    POSTGRES_PASSWORD: str = "hms_secure_password_2024"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5434
    JWT_SECRET: str = "hms-jwt-secret-change-in-production"
    AUTH_COOKIE_SECURE: bool = False
    AUTH_MAX_FAILED_ATTEMPTS: int = 5
    AUTH_LOCKOUT_MINUTES: int = 15
    AUTH_EXPOSE_RESET_TOKEN: bool = True
    ENTRA_TENANT_ID: str = ""
    ENTRA_CLIENT_ID: str = ""
    ENTRA_CLIENT_SECRET: str = ""
    ENTRA_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/entra/callback"

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{quote_plus(self.POSTGRES_USER)}:{quote_plus(self.POSTGRES_PASSWORD)}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = str(Path(__file__).resolve().parents[1] / ".env")
        extra = "ignore"


settings = Settings()

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
