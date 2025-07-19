from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://username:password@localhost/recipe_social"
    
    # Security
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # API
    api_v1_str: str = "/api/v1"
    project_name: str = "Recipe Social API"
    
    # CORS
    backend_cors_origins: list[str] = ["http://localhost:3000"]
    
    class Config:
        env_file = ".env"

settings = Settings()