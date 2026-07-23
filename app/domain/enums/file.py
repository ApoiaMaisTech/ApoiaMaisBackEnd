from enum import Enum

class FileOwnerType(str, Enum):
    PATIENT = "paciente"
    USER = "usuario"
    STORE_ITEM = "item_loja"
    ACHIEVEMENT = "conquista"

class FileCategory(str, Enum):
    AVATAR = "avatar"
    AI_MEDIA = "midia_ia"
    ITEM_IMAGE = "imagem_item"
    ACHIEVEMENT_ICON = "icone_conquista"
    OTHER = "outro"