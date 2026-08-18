
from pydantic import BaseModel


class NotebookCreate(BaseModel):
    name: str


class NotebookUpdate(BaseModel):
    name: str


class NotebookResponse(BaseModel):
    id: str
    name: str
    is_default: bool
    created_at: str
    updated_at: str
    note_count: int = 0


class NoteCreate(BaseModel):
    title: str | None = None
    content: str = ""
    raw_transcription: str | None = None


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None


class NoteResponse(BaseModel):
    id: str
    notebook_id: str
    title: str | None
    content: str
    raw_transcription: str | None
    created_at: str
    updated_at: str


class NoteListItem(BaseModel):
    id: str
    notebook_id: str
    title: str | None
    content_preview: str
    # Total character length of the raw note content (including markdown
    # syntax). The frontend uses this to estimate token counts for the
    # note-reference picker; showing only the preview length would
    # drastically under-count long notes.
    content_length: int = 0
    # Approximate token count (cl100k / tiktoken-style estimate):
    #   CJK characters   : ~1 token per character
    #   non-CJK characters: ~1 token per 4 characters
    # Computed server-side so every client renders a consistent number
    # without having to fetch the full note body.
    token_estimate: int = 0
    created_at: str
    updated_at: str


class QuickNoteCreate(BaseModel):
    transcription: str
    notebook_id: str | None = None


class NotebookBulkDelete(BaseModel):
    notebook_ids: list[str]


class NoteBulkDelete(BaseModel):
    note_ids: list[str]


class BulkDeleteResponse(BaseModel):
    status: str
    deleted_count: int


class NoteMoveRequest(BaseModel):
    target_notebook_id: str


class NoteBulkMoveRequest(BaseModel):
    note_ids: list[str]
    target_notebook_id: str


class BulkMoveResponse(BaseModel):
    status: str
    moved_count: int


class NotebookBulkExport(BaseModel):
    notebook_ids: list[str]


class NoteBulkExport(BaseModel):
    note_ids: list[str]
    format: str = "md"  # "md" or "pdf"


class NoteSearchResult(BaseModel):
    note_id: str
    notebook_id: str
    notebook_name: str
    title: str | None
    content_snippet: str
