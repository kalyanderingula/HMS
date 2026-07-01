from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    POSTGRES_DB: str = "hospital_management_system"
    POSTGRES_USER: str = "hms_admin"
    POSTGRES_PASSWORD: str = "hms_secure_password_2024"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5434
    JWT_SECRET: str = "hms-jwt-secret-change-in-production"

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

engine = create_async_engine(settings.database_url)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with async_session() as session:
        yield session
