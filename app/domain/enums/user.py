from enum import Enum

class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"