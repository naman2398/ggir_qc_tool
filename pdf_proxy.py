"""PDF proxy service for GGIR QC Tool."""

from pathlib import Path
from typing import Optional
import hashlib

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse

from config import settings
from src.api.file_operations import get_drive_id_uncached
from src.auth.msal_auth import get_access_token_uncached

app = FastAPI(title="GGIR PDF Proxy")

_CACHE_ENABLED = settings.PDF_PROXY_CACHE_ENABLED
_CACHE_DIR = Path(settings.PDF_PROXY_CACHE_DIR)
if _CACHE_ENABLED:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

_DRIVE_ID = None


def _get_drive_id(access_token: str) -> str:
    global _DRIVE_ID
    if _DRIVE_ID:
        return _DRIVE_ID
    _DRIVE_ID = get_drive_id_uncached(access_token)
    return _DRIVE_ID


def _safe_filename(name: Optional[str], file_id: str) -> str:
    if name:
        cleaned = name.replace("\"", "").replace("\\", "")
        if cleaned:
            return cleaned
    return f"{file_id}.pdf"


def _cache_path(file_id: str) -> Path:
    digest = hashlib.sha256(file_id.encode("utf-8")).hexdigest()
    return _CACHE_DIR / f"{digest}.pdf"


def _stream_response(resp: requests.Response):
    try:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            if chunk:
                yield chunk
    finally:
        resp.close()


def _stream_and_cache(resp: requests.Response, cache_path: Path):
    temp_path = cache_path.with_suffix(".tmp")
    try:
        with temp_path.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    fh.write(chunk)
                    yield chunk
        temp_path.replace(cache_path)
    finally:
        resp.close()
        if temp_path.exists() and not cache_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/pdf/{file_id:path}")
def get_pdf(file_id: str, name: Optional[str] = Query(default=None)):
    try:
        access_token = get_access_token_uncached()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        drive_id = _get_drive_id(access_token)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Drive lookup failed: {exc}") from exc

    filename = _safe_filename(name, file_id)
    headers = {"Content-Disposition": f'inline; filename="{filename}"'}

    cache_path = None
    if _CACHE_ENABLED:
        cache_path = _cache_path(file_id)
        if cache_path.exists():
            def _stream_file():
                with cache_path.open("rb") as fh:
                    while True:
                        chunk = fh.read(1024 * 1024)
                        if not chunk:
                            break
                        yield chunk

            return StreamingResponse(_stream_file(), media_type="application/pdf", headers=headers)

    url = f"{settings.GRAPH_API_ENDPOINT}/drives/{drive_id}/items/{file_id}/content"
    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
        stream=True,
        timeout=60,
    )

    if resp.status_code != 200:
        resp.close()
        raise HTTPException(status_code=resp.status_code, detail="Failed to fetch PDF.")

    media_type = resp.headers.get("Content-Type", "application/pdf")
    if _CACHE_ENABLED and cache_path is not None:
        return StreamingResponse(
            _stream_and_cache(resp, cache_path),
            media_type=media_type,
            headers=headers,
        )

    return StreamingResponse(_stream_response(resp), media_type=media_type, headers=headers)
