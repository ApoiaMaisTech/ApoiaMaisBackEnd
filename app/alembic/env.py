from logging.config import fileConfig

import asyncio
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool

from alembic import context

from app.core.config import settings
from app.infrastructure.database.base import Base

# Auth
from app.infrastructure.database.models.auth.user_model import UserModel

# Audit
from app.infrastructure.database.models.audit.audit_log_model import AuditLogModel
from app.infrastructure.database.models.audit.audit_log_error import AuditLogErrorModel

# File
from app.infrastructure.database.models.file.files_model import FileModel

# Notification
from app.infrastructure.database.models.notification.notification_model import NotificationModel

# Patient
from app.infrastructure.database.models.patient.guardian_model import GuardianModel
from app.infrastructure.database.models.patient.patient_model import PatientModel
from app.infrastructure.database.models.patient.patient_clinical import PatientClinicalModel
from app.infrastructure.database.models.patient.patient_inventory_model import PatientInventoryModel

# Ludic
from app.infrastructure.database.models.ludic.store_item_model import StoreItemModel
from app.infrastructure.database.models.ludic.achievement_model import AchievementModel
from app.infrastructure.database.models.ludic.patient_achievement_model import PatientAchievementModel
from app.infrastructure.database.models.ludic.world_model import WorldModel
from app.infrastructure.database.models.ludic.stage_model import StageModel
from app.infrastructure.database.models.ludic.patient_progress_model import PatientProgressModel
from app.infrastructure.database.models.ludic.ai_content_model import AIContentModel

__all__ = [
    "UserModel",
    "AuditLogModel",
    "AuditLogErrorModel",
    "FileModel",
    "NotificationModel",
    "GuardianModel",
    "PatientModel",
    "PatientClinicalModel",
    "PatientInventoryModel",
    "StoreItemModel",
    "AchievementModel",
    "PatientAchievementModel",
    "WorldModel",
    "StageModel",
    "PatientProgressModel",
    "AIContentModel",
]


# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

config.set_main_option(
    "sqlalchemy.url",
    settings.DATABASE_URL.replace("%", "%%")
)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations():

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(
            do_run_migrations
        )

    await connectable.dispose()


def do_run_migrations(connection):

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():

    asyncio.run(
        run_async_migrations()
    )


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
