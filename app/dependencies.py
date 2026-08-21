from app.config import settings, Settings
from app.state import system_state, SystemState

def get_settings() -> Settings:
    return settings

def get_system_state() -> SystemState:
    return system_state
