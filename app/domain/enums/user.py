from enum import Enum

class UserRole(str, Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    