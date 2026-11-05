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

    # Where the backend and the web app are reachable from the browser (for redirects after Microsoft sign-in)
    PUBLIC_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    # Exams with allowed networks: use X-Forwarded-For for the student's IP (only behind your own reverse proxy)
    TRUST_PROXY_HEADERS: bool = False

    # Sign in with Microsoft (faculty accounts). Off unless MS_CLIENT_ID and MS_CLIENT_SECRET are set.
    MS_CLIENT_ID: str = ""
    MS_CLIENT_SECRET: str = ""
    MS_TENANT_ID: str = "organizations"   # the faculty's tenant id/domain, or "organizations" for any work account
    MS_ALLOWED_DOMAINS: str = ""          # e.g. "students.finki.ukim.mk,finki.ukim.mk" (empty = any)
    MS_AUTHORITY: str = ""                # override (tests); default https://login.microsoftonline.com/<tenant>/v2.0

    # Per-student limits (0 = no limit). Admins are never limited.
    RATE_AI_PER_MINUTE: int = 10     # AI requests (step check, hint, explanation, ...) per minute
    RATE_AI_PER_DAY: int = 300       # AI provider calls per 24 hours
    RATE_TESTS_PER_MINUTE: int = 20  # "Run tests" per minute
    RATE_CHECKS_PER_MINUTE: int = 20  # editor compiler checks per minute (extra ones are skipped silently)

    # E-mail. MAIL_MODE: "preview" (nothing leaves the server: messages are only shown in the app — for testing),
    # "smtp" (the faculty's mail server) or "microsoft" (Microsoft 365 / Exchange Online through Microsoft Graph,
    # with the MS_CLIENT_ID / MS_CLIENT_SECRET / MS_TENANT_ID app; it needs the Mail.Send application permission).
    MAIL_MODE: str = "preview"
    MAIL_FROM: str = "ale@localhost"           # sender address (SMTP) / mailbox that sends (Microsoft)
    MAIL_FROM_NAME: str = "ALE"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_SECURITY: str = "starttls"            # starttls | ssl | none
    REMINDER_CHECK_MINUTES: int = 5            # how often deadline reminders are looked for

    # Load (an exam with a few hundred students at once)
    DB_POOL_SIZE: int = 20            # database connections kept open by each backend process
    DB_MAX_OVERFLOW: int = 30         # extra connections under load
    SUBMISSION_WORKERS: int = 4       # submissions tested at the same time — match RUNNER_WORKERS × code-runner replicas
    SUBMIT_WAIT_SECONDS: float = 20   # how long "Submit" waits for the result before answering "queued"
    RUNNER_BUSY_RETRY_SECONDS: float = 120  # keep retrying a busy code runner this long before giving up

    class Config:
        env_file = ".env"


settings = Settings()
