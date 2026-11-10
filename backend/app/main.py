from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.llm.faq_bot import DEFAULT_VERSION, answer, list_versions, live_version

app = FastAPI()

class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    version: str | None = None  # any registry version; None = the default (live) version


class AskResponse(BaseModel):
    answer: str
    version: str


class VersionInfo(BaseModel):
    version: str
    description: str


class VersionsResponse(BaseModel):
    default: str
    live: str
    versions: list[VersionInfo]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/versions")
def versions() -> VersionsResponse:
    """Registry versions for the chat UI's version selector."""
    entries = list_versions()
    return VersionsResponse(
        default=DEFAULT_VERSION,
        live=live_version(),
        versions=[VersionInfo(version=v, description=e.get("description", "")) for v, e in entries.items()],
    )


@app.post("/api/faq")
def ask(request: AskRequest) -> AskResponse:
    version = request.version or DEFAULT_VERSION
    if version not in list_versions():
        raise HTTPException(status_code=422, detail="unknown_version")
    try:
        text, _, _ = answer(request.question, version)
    except Exception as error:  # OpenAI errors, timeouts, incomplete responses
        logger.error(f"Error answering question: {error}")
        raise HTTPException(status_code=502, detail="model_error") from error
    return AskResponse(answer=text, version=version)
