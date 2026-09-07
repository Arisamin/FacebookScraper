# Phase 6: Sandbox Test Plan & Verification Guide

> **Target Environment**: Local Dev / Hetzner VPS (`http://localhost:8000`)  
> **Repository**: `FacebookScraper`

---

## 1. Overview
This test plan provides comprehensive steps to verify all components of the Facebook Scraper pipeline:
1. **CLI Direct Execution** (Natural language query to formatted output)
2. **FastAPI n8n Bridge Server** (`/api/v1/health`, `/api/v1/compile`, `/api/v1/scrape`)
3. **n8n Workflow Webhook Integration** (`n8n_workflows/facebook_scraper_workflow.json`)

---

## 2. Test Cases

### Test Case 1: CLI Natural Language End-to-End Run (Mock/Dry-Run)
Run the main entrypoint with a natural language task:
```powershell
python main.py "Extract the latest 5 posts mentioning AI tools from target group" --format markdown
```
**Expected Outcome**:
- Task compiler outputs validated manifest.
- Scraper executes (or falls back to mock if no live credentials present).
- Output Synthesizer displays a formatted Markdown table of extracted posts.

---

### Test Case 2: FastAPI n8n Bridge Server Health & Compilation Check
1. Start the bridge server in background mode:
```powershell
uvicorn src.n8n_bridge.server:app --host 0.0.0.0 --port 8000
```
2. Verify Health:
```powershell
curl http://localhost:8000/api/v1/health
```
**Expected Response**:
```json
{"status": "ok", "service": "facebook-scraper-n8n-bridge", "version": "1.0.0"}
```

3. Test NL Task Compilation via HTTP:
```powershell
curl -X POST http://localhost:8000/api/v1/compile -H "Content-Type: application/json" -d '{\"prompt\": \"Scrape 10 posts from Python Devs group\"}'
```

---

### Test Case 3: n8n Workflow Verification
1. Open n8n dashboard (e.g. on your Hetzner instance or local container).
2. Import `n8n_workflows/facebook_scraper_workflow.json`.
3. Configure the Webhook node and trigger an execution with payload:
```json
{
  "prompt": "Find top discussions about LLM agents in Facebook AI group",
  "format": "markdown"
}
```
4. Verify n8n triggers the FastAPI bridge and returns formatted Markdown / CSV.

---

## 3. Sign-Off Checklist
- [ ] Pytest suite passing (24/24 unit & integration tests)
- [ ] Task Compiler produces valid JSON manifest
- [ ] Scraper handles DOM extraction and rate limiting gracefully
- [ ] Output Synthesizer formats Markdown, CSV, and Mermaid
- [ ] FastAPI bridge responsive and ready for n8n Webhook calls
