from datetime import datetime

def current_iso_timestamp() -> str:
    return datetime.now().isoformat()
