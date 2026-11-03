from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str
    DB_PASSWORD: str = ""
    DB_NAME: str
    SQL_ECHO: bool = False

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 30

    # documentação interativa (/docs, /redoc, /openapi.json): desligada por padrão
    # para não expor o mapa de rotas; ligue só em desenvolvimento
    ENABLE_DOCS: bool = False

    # logs
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True

    # rate limiting (vazio = contadores em memória, válido só com um processo)
    REDIS_URL: str = ""
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: str = "120/minute"
    RATE_LIMIT_LOGIN: str = "5/minute"
    RATE_LIMIT_USER_CREATION: str = "20/minute"
    RATE_LIMIT_AI_IMAGE: str = "30/minute"

    # mensageria (usada só pelo worker: python -m app.worker)
    RABBITMQ_URL: str = ""
    MESSAGING_MAX_RETRIES: int = 3
    MESSAGING_PREFETCH: int = 10
    OUTBOX_POLL_INTERVAL_SECONDS: float = 1.0
    OUTBOX_BATCH_SIZE: int = 50

    # armazenamento de mídia: "local" (volume) ou "s3" (S3/MinIO/compatível)
    STORAGE_BACKEND: str = "local"
    STORAGE_LOCAL_DIR: str = "/data/media"
    S3_ENDPOINT_URL: str = ""
    S3_BUCKET: str = ""
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""

    # imagens geradas por IA
    AI_IMAGE_DAILY_QUOTA_PER_USER: int = 20
    AI_IMAGE_FAILURE_COOLDOWN_MINUTES: int = 10

    # retenção de dados (LGPD); aplicada pelo api-worker. Auditoria: mínimo de 180 dias (Marco Civil)
    RETENTION_ENABLED: bool = True
    RETENTION_INTERVAL_HOURS: float = 24.0
    RETENTION_PROCESSED_EVENT_DAYS: int = 30
    RETENTION_OUTBOX_PUBLISHED_DAYS: int = 7
    RETENTION_ERROR_LOG_DAYS: int = 90
    RETENTION_READ_NOTIFICATION_DAYS: int = 180
    RETENTION_AUDIT_LOG_DAYS: int = 180

    # CORS: origens separadas por vírgula
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:3002,http://127.0.0.1:3002"
    )

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def jwt_secret_nao_vazio(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("JWT_SECRET_KEY não pode ser vazio")
        return value

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def retention_policy(self):
        from app.infrastructure.database.retention import RetentionPolicy

        return RetentionPolicy(
            processed_event_days=self.RETENTION_PROCESSED_EVENT_DAYS,
            outbox_published_days=self.RETENTION_OUTBOX_PUBLISHED_DAYS,
            error_log_days=self.RETENTION_ERROR_LOG_DAYS,
            read_notification_days=self.RETENTION_READ_NOTIFICATION_DAYS,
            audit_log_days=self.RETENTION_AUDIT_LOG_DAYS,
        )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"



settings = Settings()
