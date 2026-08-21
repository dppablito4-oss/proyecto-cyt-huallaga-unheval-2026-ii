import uuid

def generate_event_id() -> str:
    return str(uuid.uuid4())
