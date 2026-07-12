"""Notes API protected by the pico auth pair: pico-server-auth issues the
JWTs (embedded, /api/v1/auth/*) and pico-client-auth validates them on
every request. Reads are public; writes need a token; deletes need the
admin role."""

import itertools

from fastapi import HTTPException
from pydantic import BaseModel

from pico_client_auth import allow_anonymous, requires_role
from pico_fastapi import controller, delete, get, post
from pico_ioc import component


class NoteRequest(BaseModel):
    text: str


@component
class NotesStore:
    def __init__(self):
        self._notes: dict[int, str] = {}
        self._ids = itertools.count(1)

    def add(self, text: str) -> int:
        note_id = next(self._ids)
        self._notes[note_id] = text
        return note_id

    def remove(self, note_id: int) -> bool:
        return self._notes.pop(note_id, None) is not None

    def all(self) -> dict[int, str]:
        return dict(self._notes)


@controller(prefix="/api/v1/notes", tags=["Notes"])
class NotesController:
    def __init__(self, store: NotesStore):
        self._store = store

    @allow_anonymous
    @get("")
    async def list_notes(self):
        return [{"id": i, "text": t} for i, t in self._store.all().items()]

    @post("")
    async def create_note(self, request: NoteRequest):
        return {"id": self._store.add(request.text)}

    @requires_role("admin")
    @delete("/{note_id}")
    async def delete_note(self, note_id: int):
        if not self._store.remove(note_id):
            raise HTTPException(status_code=404, detail="no such note")
        return {"deleted": note_id}
