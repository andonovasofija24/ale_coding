from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str = "supersecretkey"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    OPENAI_API_KEY: str
    CODE_RUNNER_URL: str = "http://code-runner:8001"
    CODE_RUNNER_SECRET: str = "runner_secret"
    FIRST_ADMIN_EMAIL: str = "admin@example.com"
    FIRST_ADMIN_PASSWORD: str = "adminpassword"
    FIRST_ADMIN_NAME: str = "Admin"

    class Config:
        env_file = ".env"


settings = Settings()
