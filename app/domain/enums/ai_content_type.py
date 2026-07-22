from enum import Enum


class AIContentType(str, Enum):
    STORY = "story"
    IMAGE = "image"
    EXERCISE = "exercise"
    AUDIO = "audio"