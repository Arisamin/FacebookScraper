"""n8n Bridge Server: REST API endpoints for seamless n8n webhook and AI agent integration."""

from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.models.manifest import TaskManifest, OutputFormat
from src.models.post import PostPayload, GroupRecord
from src.compiler.task_compiler import TaskCompiler
from src.scraper.engine import ScraperEngine
from src.synthesizer.formatters import OutputSynthesizer

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


class SessionInjectRequest(BaseModel):
    storage_state: Dict[str, Any]


class LoginRequest(BaseModel):
    timeout_seconds: int = 120


@app.get("/health")
def health():
    return {"status": "ok", "service": "FacebookScraper Bridge"}


@app.get("/session/status")
def session_status():
    """Check if an active session exists in session_storage.json."""
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
