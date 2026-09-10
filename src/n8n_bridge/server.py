"""n8n Bridge Server: REST API endpoints for seamless n8n webhook and AI agent integration."""

import os
import sys
import asyncio

# Ensure Windows Proactor event loop policy is active for Playwright subprocess support
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import logging
from logging.handlers import RotatingFileHandler
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.models.manifest import TaskManifest, OutputFormat
from src.models.post import PostPayload, GroupRecord
from src.compiler.task_compiler import TaskCompiler
from src.scraper.engine import ScraperEngine
from src.synthesizer.formatters import OutputSynthesizer

# Ensure logs directory exists
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE_PATH = os.path.join(LOGS_DIR, "scraper.log")

# Configure root logger to output to both console and logs/scraper.log
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Formatter
log_formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

# File Handler (5 MB max, 3 backups)
if not any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers):
    file_handler = RotatingFileHandler(LOG_FILE_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)

logger = logging.getLogger("BridgeServer")
logger.info(f"Logging initialized. Log file: {LOG_FILE_PATH}")

app = FastAPI(
    title="Facebook Scraper n8n Bridge API",
    version="1.0.0",
    description="Bridge API providing compilation, scraping, and synthesis nodes for n8n workflows.",
)

compiler = TaskCompiler()
scraper = ScraperEngine()
synthesizer = OutputSynthesizer()


class CompileRequest(BaseModel):
    prompt: str


class SynthesizeRequest(BaseModel):
    posts: List[PostPayload] = []
    group_records: List[GroupRecord] = []
    format: str = "markdown_table"
    columns: Optional[List[str]] = None
    custom_instructions: Optional[str] = None
    original_prompt: Optional[str] = None


class PipelineRequest(BaseModel):
    prompt: str
    headless: bool = True


class ScrapeRequest(BaseModel):
    manifest: TaskManifest
    headless: bool = True


class ObstacleRequest(BaseModel):
    screenshot_base64: str
    target_action: str = "expand_see_more"


class DiagnosticRequest(BaseModel):
    manifest: Optional[TaskManifest] = None
    posts: List[PostPayload] = []
    group_records: List[GroupRecord] = []
    original_prompt: Optional[str] = None
    error_message: Optional[str] = None


class SessionInjectRequest(BaseModel):
    storage_state: Dict[str, Any]


class LoginRequest(BaseModel):
    timeout_seconds: int = 120


@app.get("/health")
def health():
    return {"status": "ok", "service": "FacebookScraper Bridge"}


@app.get("/logs")
def get_logs(lines: int = 100):
    """Retrieve recent application log lines for troubleshooting and diagnostics."""
    if not os.path.exists(LOG_FILE_PATH):
        return {"logs": [], "total_lines": 0}
    try:
        with open(LOG_FILE_PATH, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            return {
                "logs": [l.strip() for l in recent_lines],
                "total_lines": len(all_lines),
                "log_file": LOG_FILE_PATH,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/status")
async def session_status(live_check: bool = True):
    """Check if an active session exists and is live/accepted on Facebook."""
    if live_check:
        valid = await scraper.session_manager.check_live_session()
    else:
        valid = scraper.session_manager.has_valid_session()
    return {
        "has_valid_session": valid,
        "storage_state_path": scraper.session_manager.storage_state_path,
    }


@app.post("/session/login")
async def trigger_login(req: LoginRequest = LoginRequest()):
    """Trigger an interactive login window to capture fresh session cookies."""
    success = await scraper.session_manager.launch_interactive_login(timeout_seconds=req.timeout_seconds)
    if success:
        return {"status": "authenticated", "has_valid_session": True}
    return {
        "status": "timeout_or_unauthenticated",
        "has_valid_session": False,
        "message": "Login window closed or timed out before authentication cookies were detected."
    }


@app.post("/session/inject")
def inject_session(req: SessionInjectRequest):
    """Inject a storage state JSON (cookies & localStorage) programmatically."""
    scraper.session_manager.save_storage_state(req.storage_state)
    return {"status": "injected", "has_valid_session": True}


@app.post("/scrape")
async def scrape_endpoint(req: ScrapeRequest):
    """Execute raw Playwright scraping for a given TaskManifest."""
    try:
        posts, group_records = await scraper.execute_task(req.manifest, headless=req.headless)
        return {
            "status": "success",
            "posts": [p.model_dump() for p in posts],
            "group_records": [g.model_dump() for g in group_records],
            "posts_count": len(posts),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/diagnose")
def diagnose_obstacle(req: DiagnosticRequest):
    """Use Gemini AI to analyze scraping failure/obstacle context and return actionable explanation."""
    import json
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not gemini_key:
        gated = [g for g in req.group_records if g.requires_joining]
        if any(g.group_name == "Authentication Required" for g in req.group_records):
            msg = "Facebook session has expired or was challenged with a login screen. Please re-authenticate via login.py."
        elif gated and len(gated) == len(req.group_records):
            msg = f"Discovered groups are private and require membership approval."
        elif len(req.group_records) == 0:
            msg = "No Facebook groups or posts were found matching the search query."
        else:
            msg = f"Scanned {len(req.group_records)} group(s), but 0 posts matched the filter criteria."
        return {"obstacle_detected": True, "diagnostic": msg}

    import urllib.request
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"

    context_data = {
        "original_prompt": req.original_prompt,
        "manifest_target": req.manifest.target.model_dump() if req.manifest else None,
        "group_records": [g.model_dump() for g in req.group_records],
        "posts_scraped_count": len(req.posts),
        "error_message": req.error_message,
    }

    prompt = (
        "You are an expert Facebook Scraper Diagnostic AI agent.\n"
        "A scraping job returned 0 posts or encountered an obstacle. Analyze the execution context:\n"
        f"{json.dumps(context_data, indent=2)}\n\n"
        "Provide a concise, user-friendly, and precise 1-2 sentence explanation of why the scrape returned 0 posts "
        "and what the user or system should do (e.g. re-authenticate with fresh session cookies, broaden search keywords, or join private groups). "
        "Output ONLY the explanation without preamble."
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }

    try:
        http_req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(http_req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            diagnostic_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return {"obstacle_detected": True, "diagnostic": diagnostic_text}
    except Exception as e:
        logger.warning(f"AI diagnostic call failed: {e}")
        return {"obstacle_detected": True, "diagnostic": "Scrape completed with 0 results or encountered a session challenge."}


@app.post("/solve-obstacle")
def solve_obstacle(req: ObstacleRequest):
    """Use AI vision to locate coordinates or resolve obstacles in a screenshot."""
    import base64
    try:
        img_bytes = base64.b64decode(req.screenshot_base64)
        location = scraper.vision_handler.locate_target_in_crop(img_bytes, req.target_action)
        if location:
            return {"status": "success", "element_location": location.model_dump()}
        return {"status": "unresolved", "message": "Could not identify target action visually"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/compile", response_model=TaskManifest)
def compile_prompt(req: CompileRequest):
    """Compile human natural language request into a TaskManifest JSON."""
    try:
        manifest = compiler.compile(req.prompt)
        return manifest
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/pipeline")
async def run_pipeline(req: PipelineRequest):
    """Run full end-to-end pipeline: compile NL prompt -> execute scrape -> synthesize."""
    try:
        manifest = compiler.compile(req.prompt)
        posts, group_records = await scraper.execute_task(manifest, headless=req.headless)

        formatted = synthesizer.synthesize(
            posts=posts,
            group_records=group_records,
            format=manifest.output_config.format,
            columns=manifest.output_config.columns,
            custom_instructions=manifest.output_config.custom_instructions,
            original_prompt=req.prompt,
        )

        return {
            "status": "success",
            "task_id": manifest.task_id,
            "manifest": manifest,
            "posts_count": len(posts),
            "gated_groups_count": len([g for g in group_records if g.requires_joining]),
            "formatted_output": formatted,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/synthesize")
def synthesize_data(req: SynthesizeRequest):
    """Synthesize post and group records into any requested format using AI or deterministic rules."""
    try:
        formatted = synthesizer.synthesize(
            posts=req.posts,
            group_records=req.group_records,
            format=req.format,
            columns=req.columns,
            custom_instructions=req.custom_instructions,
            original_prompt=req.original_prompt,
        )

        return {
            "format": req.format,
            "formatted_output": formatted,
            "posts_count": len(req.posts),
            "gated_groups_count": len([g for g in req.group_records if g.requires_joining]),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
