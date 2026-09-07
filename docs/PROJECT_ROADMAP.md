# Facebook Scraper Project Roadmap & Phase Tracker

> **Pinned Tracker File**  
> Location: `docs/PROJECT_ROADMAP.md`  
> Working Directory: `c:\MyData\Git\FacebookScraper`

---

## **Visual Workflow & Phase Architecture**

```
┌────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Architecture & Data Schemas (docs/ARCHITECTURE.md)           │
│ └── Mode: Main Session (Interactive Collaboration)                     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ Phase 2: TDD Component 1 — Task Compiler (NL ➔ JSON Manifest)          │
│ └── Mode: Main Session + task Subagent (Silent Test Running)           │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ Phase 3: TDD Component 2 — Playwright & Semantic Extractor             │
│ └── Mode: Forked Session (/fork browser-tdd) or Explore Subagent       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ Phase 4: TDD Component 3 — Output Synthesizer (Tables, CSV, Diagrams)  │
│ └── Mode: Main Session + task Subagent (Fast Red-Green Cycles)         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ Phase 5: n8n Workflow Packaging & Hetzner Deployment (.json)           │
│ └── Mode: Main Session + research Subagent (n8n API verification)      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│ Phase 6: Manual Sandbox Test Plan for Live Verification                │
│ └── Mode: Main Session (Interactive Execution & Review)                │
└────────────────────────────────────────────────────────────────────────┘
```

---

## **Phase Checklist & CLI Execution Modes**

- [x] **Phase 1: Architecture & Specification**
  - **Goal**: Lock in JSON schemas, target Facebook surfaces, extraction payloads, and error states in `docs/ARCHITECTURE.md`.
  - **Status**: ✅ Completed & Documented in `docs/ARCHITECTURE.md`.

- [x] **Phase 2: TDD Component 1 — Human Language Task Compiler**
  - **Goal**: Converts natural human language prompts into validated structured JSON manifests.
  - **Status**: ✅ Completed & Tested (`tests/test_task_compiler.py`).

- [x] **Phase 3: TDD Component 2 — Resilient Playwright & Semantic Extractor**
  - **Goal**: Anti-detection, cookie manager, accessibility tree DOM extraction, and AI obstacle recovery.
  - **Status**: ✅ Completed & Tested (`tests/test_dom_extractor.py`, `tests/test_group_scanner.py`, `tests/test_vision_fallback.py`).

- [x] **Phase 4: TDD Component 3 — Output Synthesizer & Formatters**
  - **Goal**: Converts extracted post payloads into Markdown tables, CSV exports, text summaries, and Mermaid diagrams.
  - **Status**: ✅ Completed & Tested (`tests/test_output_synthesizer.py`).

- [x] **Phase 5: n8n Workflow Packaging & Hetzner Deployment**
  - **Goal**: Assemble tested components into ready-to-import n8n workflow templates (`.json`) and FastAPI bridge for your Hetzner instance.
  - **Status**: ✅ Completed & Tested (`n8n_workflows/facebook_scraper_workflow.json`, `tests/test_n8n_bridge.py`).

- [ ] **Phase 6: Manual Sandbox Test Plan & Sign-Off**
  - **Goal**: Provide a step-by-step test plan for running live scrapes and verifying data in n8n.
  - **Status**: 🔄 In Progress.
