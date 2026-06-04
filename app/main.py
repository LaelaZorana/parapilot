"""ParaPilot FastAPI app — server-rendered (Jinja + htmx).

Two main views (SPEC §7):
  * ROADMAP  — visual stepper of the IL divorce process; click a step for its
               summary, required forms (+ what each must contain), deadlines,
               who-to-call, citations, and next/branch options.
  * ASK      — grounded chat; answers carry inline citations + confidence + the
               disclaimer; out-of-scope/advice -> visible refusal + escalation.

Everything runs offline on the stub provider with no API keys.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app import __version__
from app.config import get_settings
from app.db import get_db, init_db
from app.deps import get_engine
from app.models import Matter, StepProgress
from app.rag.corpus import corpus_stats
from app.rag.generate import answer_question
from app.safety.disclaimers import (
    DISCLAIMER,
    DISCLAIMER_LONG,
    FIND_HELP_NAME,
    FIND_HELP_URL,
)

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="ParaPilot",
    description="Illinois divorce procedural navigator — legal information, not legal advice.",
    version=__version__,
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _linkify_citations(answer: str, citations) -> str:
    """Turn inline [n] markers into clickable, accessible citation chips.

    The answer text is HTML-escaped first (it's source-derived but we never
    trust-by-default), then markers are replaced with anchors to the matching
    citation's source URL. Markers without a matching citation are dropped.
    """
    import html
    import re

    by_marker = {c.marker: c for c in citations}
    safe = html.escape(answer)

    def repl(m):
        n = m.group(1)
        c = by_marker.get(n)
        if not c:
            return ""
        title = html.escape("{} — {}".format(c.publisher, c.title))
        return (
            '<a href="{url}" target="_blank" rel="noopener" class="pp-cite" '
            'title="{title}">{n}</a>'
        ).format(url=html.escape(c.url, quote=True), title=title, n=n)

    return re.sub(r"\[(\d+)\]", repl, safe)


templates.env.filters["linkify_citations"] = _linkify_citations


# --- global template context ------------------------------------------------
@app.middleware("http")
async def add_no_cache_for_htmx(request: Request, call_next):
    response = await call_next(request)
    if request.headers.get("HX-Request"):
        response.headers["Cache-Control"] = "no-store"
    return response


def _base_ctx(request: Request) -> dict:
    return {
        "request": request,
        "version": __version__,
        "disclaimer": DISCLAIMER,
        "disclaimer_long": DISCLAIMER_LONG,
        "find_help_name": FIND_HELP_NAME,
        "find_help_url": FIND_HELP_URL,
    }


@app.on_event("startup")
def _startup() -> None:
    init_db()
    # Warm the engine + retriever so first request is fast and config errors
    # surface at boot rather than mid-request.
    get_engine()


# --- pages ------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    engine = get_engine()
    ctx = _base_ctx(request)
    ctx.update(
        {
            "flow": engine.flow,
            "main_line": engine.main_line(),
            "subflows": engine.subflows(),
            "stats": corpus_stats(),
            "active": "roadmap",
        }
    )
    return templates.TemplateResponse(request, "roadmap.html", ctx)


@app.get("/step/{step_id}", response_class=HTMLResponse)
def step_detail(request: Request, step_id: str):
    """htmx partial: the detail panel for one step."""
    engine = get_engine()
    step = engine.get(step_id)
    if step is None:
        return HTMLResponse("<div class='p-6 text-rose-600'>Unknown step.</div>", status_code=404)
    ctx = _base_ctx(request)
    ctx.update(
        {
            "step": step,
            "next_steps": engine.next_steps(step_id),
            "branches": engine.branches(step_id),
        }
    )
    return templates.TemplateResponse(request, "partials/step_detail.html", ctx)


@app.get("/ask", response_class=HTMLResponse)
def ask_page(request: Request):
    ctx = _base_ctx(request)
    ctx.update(
        {
            "active": "ask",
            "examples": [
                "How long must I live in Illinois before I can file?",
                "What can I do if I can't find my spouse to serve them?",
                "Can I appear by Zoom for my hearing?",
                "Do parents have to take a parenting class?",
                "What if I can't afford the filing fee?",
            ],
        }
    )
    return templates.TemplateResponse(request, "ask.html", ctx)


@app.post("/ask", response_class=HTMLResponse)
def ask_submit(request: Request, question: str = Form(...)):
    """htmx partial: the grounded answer (or refusal) card."""
    env = answer_question(question)
    ctx = _base_ctx(request)
    ctx.update({"env": env})
    return templates.TemplateResponse(request, "partials/answer.html", ctx)


# --- saved progress (SQLite) ------------------------------------------------
@app.post("/matter", response_class=JSONResponse)
def create_matter(db: Session = Depends(get_db), label: Optional[str] = Form(None)):
    matter = Matter(label=label or "My Illinois divorce")
    db.add(matter)
    db.commit()
    return {"id": matter.id, "label": matter.label}


@app.post("/matter/{matter_id}/step/{step_id}", response_class=HTMLResponse)
def toggle_step(
    request: Request,
    matter_id: int,
    step_id: str,
    done: str = Form("true"),
    db: Session = Depends(get_db),
):
    """htmx: mark a step done/undone for a saved matter, return the chip."""
    engine = get_engine()
    if engine.get(step_id) is None:
        return HTMLResponse("Unknown step", status_code=404)

    is_done = done.lower() in {"true", "1", "on", "yes"}
    sp = (
        db.query(StepProgress)
        .filter(StepProgress.matter_id == matter_id, StepProgress.step_id == step_id)
        .one_or_none()
    )
    if sp is None:
        sp = StepProgress(matter_id=matter_id, step_id=step_id, done=is_done)
        db.add(sp)
    else:
        sp.done = is_done
    db.commit()

    ctx = _base_ctx(request)
    ctx.update({"step_id": step_id, "matter_id": matter_id, "done": is_done})
    return templates.TemplateResponse(request, "partials/progress_chip.html", ctx)


# --- about / verify-checklist / health --------------------------------------
@app.get("/about", response_class=HTMLResponse)
def about(request: Request):
    engine = get_engine()
    ctx = _base_ctx(request)
    ctx.update({"active": "about", "verify_items": engine.verify_items()})
    return templates.TemplateResponse(request, "about.html", ctx)


@app.get("/healthz", response_class=JSONResponse)
def healthz():
    settings = get_settings()
    return {
        "status": "ok",
        "version": __version__,
        "provider": settings.provider,
        "corpus": corpus_stats(),
    }


# --- JSON API (handy for the eval / integration) ----------------------------
@app.get("/api/ask", response_class=JSONResponse)
def api_ask(q: str):
    env = answer_question(q)
    return env.model_dump()
