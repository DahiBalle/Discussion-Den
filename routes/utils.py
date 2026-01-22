from __future__ import annotations

from dataclasses import dataclass

from flask import session
from flask_login import current_user

from models import Persona


@dataclass(frozen=True)
class IdentityContext:
    """
    Identity resolution used across routes and APIs.

    Why: business logic stays out of templates; routes use one shared, tested mental model.
    """

    active_persona: Persona | None

    @property
    def is_persona(self) -> bool:
        return self.active_persona is not None

    @property
    def label(self) -> str:
        return self.active_persona.name if self.active_persona else current_user.username

    @property
    def persona_id(self) -> int | None:
        return self.active_persona.id if self.active_persona else None

    @property
    def user_id(self) -> int:
        return int(current_user.id)


def get_active_persona() -> Persona | None:
    """
    Session-driven persona resolution.

    Enforces ownership: if the session points at a persona not owned by the user,
    we silently reset to default identity.
    """
    persona_id = session.get("active_persona_id")
    if not persona_id:
        return None

    persona = Persona.query.get(int(persona_id))
    if not persona or persona.user_id != current_user.id:
        session["active_persona_id"] = None
        return None
    return persona


def get_identity() -> IdentityContext:
    return IdentityContext(active_persona=get_active_persona())

