from enum import Enum

class NotificationType(str, Enum):
    ACHIEVEMENT = "conquista"
    PROGRESS = "progresso"
    SYSTEM = "sistema"
    REMINDER = "lembrete"