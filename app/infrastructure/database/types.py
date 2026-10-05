from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.dialects import mysql

# DATETIME(3) no MySQL, igual às migrations; valores sempre em UTC sem tzinfo
DateTime3 = DateTime().with_variant(mysql.DATETIME(fsp=3), "mysql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
