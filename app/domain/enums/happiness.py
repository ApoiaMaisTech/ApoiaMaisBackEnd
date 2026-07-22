from enum import Enum

class Happiness(str, Enum):
    HAPPY = "feliz"
    SAD = "triste"
    NEUTRAL = "neutra"
    ANGRY = "irritado"  