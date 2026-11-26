"""In-memory store for generated test sets (answers stay on the server)."""
import time
import uuid

TTL_SECONDS = 2 * 60 * 60
_STORE: dict[str, dict] = {}


def _purge() -> None:
    now = time.time()
    for key in [k for k, v in _STORE.items() if now - v["created"] > TTL_SECONDS]:
        del _STORE[key]


def put(kind: str, meta: dict, items: list) -> str:
    _purge()
    set_id = uuid.uuid4().hex
    _STORE[set_id] = {"kind": kind, "meta": meta, "items": items, "created": time.time()}
    return set_id


def get(set_id: str, kind: str):
    _purge()
    entry = _STORE.get(set_id)
    if entry is None or entry["kind"] != kind:
        return None
    return entry
