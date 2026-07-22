from enum import Enum

class AuditAction(str, Enum):
    CREATE = "criar"
    UPDATE = "atualizar"
    DELETE = "deletar"
    LOGIN = "login"
    LOGOUT = "logout"
    VIEW = "visualizar"

class LogLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"