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
    format: OutputFormat = OutputFormat.CSV
    columns: Optional[List[str]] = None


class PipelineRequest(BaseModel):
    prompt: str
    headless: bool = True


@app.get("/health")
def health():
    return {"status": "ok", "service": "FacebookScraper Bridge"}


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

        if manifest.output_config.format == OutputFormat.CSV:
            formatted = synthesizer.format_csv(posts, group_records, manifest.output_config.columns)
        elif manifest.output_config.format == OutputFormat.MARKDOWN_TABLE:
            formatted = synthesizer.format_markdown_table(posts, group_records, manifest.output_config.columns)
        elif manifest.output_config.format == OutputFormat.DIAGRAM_MERMAID:
            formatted = synthesizer.format_mermaid_diagram(posts, group_records)
        else:
            formatted = synthesizer.format_json(posts, group_records)

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
    """Synthesize post and group records into requested format (CSV, Markdown, Mermaid, JSON)."""
    try:
        if req.format == OutputFormat.CSV:
            formatted = synthesizer.format_csv(req.posts, req.group_records, req.columns)
        elif req.format == OutputFormat.MARKDOWN_TABLE:
            formatted = synthesizer.format_markdown_table(req.posts, req.group_records, req.columns)
        elif req.format == OutputFormat.DIAGRAM_MERMAID:
            formatted = synthesizer.format_mermaid_diagram(req.posts, req.group_records)
        else:
            formatted = synthesizer.format_json(req.posts, req.group_records)

        return {
            "format": req.format,
            "formatted_output": formatted,
            "posts_count": len(req.posts),
            "gated_groups_count": len([g for g in req.group_records if g.requires_joining]),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
