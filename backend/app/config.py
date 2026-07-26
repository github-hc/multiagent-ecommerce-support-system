from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    env: str = "development"

    class Config:
        env_file = ".env"

settings = Settings()