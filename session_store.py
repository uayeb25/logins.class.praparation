from typing import Dict

class SessionStore:
    def __init__(self):
        self.store: Dict[str, str] = {}

    def set(self, key: str, value: str):
        self.store[key] = value

    def get(self, key: str) -> str:
        return self.store.get(key)

    def delete(self, key: str):
        if key in self.store:
            del self.store[key]

session_store = SessionStore()