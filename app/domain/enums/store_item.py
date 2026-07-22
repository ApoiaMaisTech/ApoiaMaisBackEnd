from enum import Enum


class StoreItemType(str, Enum):
    AVATAR = "avatar"
    BACKGROUND = "fundo"
    ACCESSORY = "acessorio"