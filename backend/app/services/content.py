"""Task text in the reader's language: the original (title/description, written in task.content_lang) or its
translation in task.translations, falling back to the original when there is no translation."""
from app.models.task import Task

TASK_KINDS = ("code", "document", "project", "offline")
CONTENT_LANGS = ("mk", "en")


def localized(task: Task, lang: str | None) -> tuple[str, str]:
    """`lang` None (the client did not say which language it reads): the original text."""
    if lang and lang != (task.content_lang or "en"):
        tr = (task.translations or {}).get(lang) or {}
        if tr.get("title") or tr.get("description"):
            return tr.get("title") or task.title, tr.get("description") or task.description
    return task.title, task.description


def title(task: Task, lang: str | None) -> str:
    return localized(task, lang)[0]


# The reader's language for the current request (set by `use_language`, a router dependency), so helpers deep in
# the code can localize task titles without passing the language around.
from contextvars import ContextVar  # noqa: E402

from typing import Optional  # noqa: E402

from fastapi import Header  # noqa: E402

from app.core.language import Lang, parse_language  # noqa: E402

_current: ContextVar[Optional[str]] = ContextVar("content_lang", default=None)


async def reader_language(accept_language: Optional[str] = Header(default=None)) -> Optional[Lang]:
    """The language the reader asked for, or None when the request doesn't say (then texts stay original)."""
    return parse_language(accept_language) if accept_language else None


async def use_language(accept_language: Optional[str] = Header(default=None)) -> Optional[str]:
    lang = await reader_language(accept_language)
    _current.set(lang)
    return lang


def t_title(task: Task) -> str:
    return title(task, _current.get())
