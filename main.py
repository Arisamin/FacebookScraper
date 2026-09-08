"""Main entry point for FacebookScraper CLI and FastAPI server."""

import argparse
import asyncio
import sys
import uvicorn
from src.compiler.task_compiler import TaskCompiler
from src.scraper.engine import ScraperEngine
from src.synthesizer.formatters import OutputSynthesizer
from src.n8n_bridge.server import app


def run_cli(prompt: str, headless: bool = True):
    print(f"\n[1/3] Compiling natural language prompt: '{prompt}'...")
    compiler = TaskCompiler()
    manifest = compiler.compile(prompt)
    print(f"      Compiled TaskManifest ID: {manifest.task_id}")
    print(f"      Target: {manifest.target.type.value} -> '{manifest.target.url_or_query}'")
    print(f"      Format: {manifest.output_config.format.value}")

    print("\n[2/3] Executing Browser Scraper Engine...")
    scraper = ScraperEngine()
    posts, group_records = asyncio.run(scraper.execute_task(manifest, headless=headless))
    print(f"      Matched Posts: {len(posts)}")
    print(f"      Gated/Audited Groups: {len(group_records)}")

    print("\n[3/3] Synthesizing output...")
    synthesizer = OutputSynthesizer()
    if manifest.output_config.format.value == "csv":
        out = synthesizer.format_csv(posts, group_records, manifest.output_config.columns)
    elif manifest.output_config.format.value == "markdown_table":
        out = synthesizer.format_markdown_table(posts, group_records, manifest.output_config.columns)
    elif manifest.output_config.format.value == "diagram_mermaid":
        out = synthesizer.format_mermaid_diagram(posts, group_records)
    else:
        out = synthesizer.format_json(posts, group_records)

    print("\n======================= OUTPUT =======================")
    print(out)
    print("======================================================\n")


def main():
    parser = argparse.ArgumentParser(description="FacebookScraper AI-Augmented Engine")
    parser.add_argument("--prompt", type=str, help="Natural language scraping task")
    parser.add_argument("--server", action="store_true", help="Launch FastAPI server for n8n")
    parser.add_argument("--port", type=int, default=8000, help="Port for server")
    parser.add_argument("--headful", action="store_true", help="Run browser in headful mode")
    parser.add_argument("--login", action="store_true", help="Open interactive browser to capture Facebook login session")

    args = parser.parse_args()

    if args.login:
        from login import capture_session
        asyncio.run(capture_session())
    elif args.server:
        print(f"Starting FacebookScraper n8n Bridge Server on port {args.port}...")
        uvicorn.run(app, host="0.0.0.0", port=args.port)
    elif args.prompt:
        run_cli(args.prompt, headless=not args.headful)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
