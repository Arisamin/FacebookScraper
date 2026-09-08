# Facebook Scraper & Automation Agent: System Architecture & Specification

> **Document Status**: Phase 1 Design Specification  
> **Repository**: `FacebookScraper` (`c:\MyData\Git\FacebookScraper`)

---

## 1. Executive Architecture Overview

This project implements an AI-augmented, resilient Facebook scraping and monitoring pipeline. Traditional scrapers fail on Facebook due to obfuscated class names, dynamic DOM virtualization, and interactive overlays. This architecture solves these challenges using a **3-Tier Hybrid AI Pipeline** developed via **Test-Driven Development (TDD)** and packaged into **n8n workflows** for automated execution on a Hetzner server.

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                               TIER 1: TASK COMPILER                                     │
│  Human Natural Language Prompt ──► [LLM Task Compiler] ──► Canonical JSON Task Manifest │
└────────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                          TIER 2: RESILIENT HYBRID SCRAPER                               │
│  [Playwright Stealth Engine] ──► [Accessibility / Markdown Snapshot + Vision OCR]       │
│                                  │                                                      │
│                                  └──► [Self-Healing Obstacle Recovery (Modals/Popups)]   │
│                                  │                                                      │
│                                  └──► Structured Post Payloads                          │
└────────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
                                             ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                      TIER 3: OUTPUT SYNTHESIZER & N8N ORCHESTRATION                     │
│  [n8n Workflow Nodes] ──► [LLM Synthesis Engine]                                        │
│                           ├── Markdown Tables                                           │
│                           ├── Structured CSV / SQLite Data                              │
│                           ├── Mermaid Relationship Diagrams                             │
│                           └── Alerts & Dispatches (Telegram / Webhooks)                 │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Tier 1: Task Manifest Specification

The Task Compiler translates free-form natural language instructions into a strictly typed **Task Manifest JSON**:

### Manifest Schema (`src/models/manifest.py`)
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "TaskManifest",
  "type": "object",
  "required": ["task_id", "target", "criteria", "output_format"],
  "properties": {
    "task_id": {
      "type": "string",
      "description": "Unique identifier for this scraping mission"
    },
    "description": {
      "type": "string",
      "description": "Original human natural language prompt"
    },
    "target": {
      "type": "object",
      "required": ["type", "url_or_query"],
      "properties": {
        "type": {
          "type": "string",
          "enum": ["group", "search", "page", "marketplace"]
        },
        "url_or_query": {
          "type": "string",
          "description": "Direct URL or search query string"
        },
        "max_posts_to_scan": {
          "type": "integer",
          "default": 30
        },
        "max_scrolls": {
          "type": "integer",
          "default": 10
        }
      }
    },
    "criteria": {
      "type": "object",
      "properties": {
        "include_keywords": {
          "type": "array",
          "items": { "type": "string" }
        },
        "exclude_keywords": {
          "type": "array",
          "items": { "type": "string" }
        },
        "price_min": { "type": "number" },
        "price_max": { "type": "number" },
        "location_filter": { "type": "string" },
        "semantic_condition": {
          "type": "string",
          "description": "Complex intent rule evaluated by LLM (e.g. 'Only posts mentioning sublet for July-August')"
        }
      }
    },
    "output_format": {
      "type": "string",
      "enum": ["markdown_table", "csv", "json", "executive_summary", "mermaid_diagram"],
      "default": "markdown_table"
    },
    "actions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["type"],
        "properties": {
          "type": {
            "type": "string",
            "enum": ["telegram", "webhook", "save_file", "email"]
          },
          "target_config": {
            "type": "object"
          }
        }
      }
    }
  }
}
```

---

## 3. Tier 2: Resilient Hybrid Scraper Architecture

### Key Engineering Strategies for Zero-Maintenance Extraction

1. **Authentication & Session Persistence**:
   - Manages encrypted/sanitized browser state cookies (`cookies.json` / session profile).
   - Re-attaches to existing sessions without triggering fresh login MFA prompts.

2. **Semantic DOM & Accessibility Tree Extraction**:
   - Rather than relying on volatile CSS class names (`.x1i10hfl`), the engine extracts the clean **Accessibility Tree** and structured text blocks.
   - Converts post cards into normalized Markdown text chunks.

3. **Multimodal LLM / Vision Extraction Fallback**:
   - When text extraction is ambiguous or post content contains image-only text, the engine captures targeted element screenshots and extracts structured data using OCR/Vision.

4. **Self-Healing Obstacle Recovery Loop**:
   - Automatically detects and dismisses:
     - *"See more"* buttons on long text posts.
     - *"Log in / Sign up"* blocking dialogs.
     - Cookie consent banners and notification prompts.

### Post Payload Schema (`src/models/post.py`)
```json
{
  "post_id": "str",
  "author_name": "str",
  "author_profile_url": "str",
  "timestamp_str": "str",
  "published_iso": "str",
  "raw_text": "str",
  "extracted_price": "float | null",
  "extracted_location": "str | null",
  "media_urls": ["str"],
  "permalink": "str",
  "matched_filters": ["str"],
  "match_score": "float (0.0 to 1.0)"
}
```

---

## 4. Tier 3: Output Synthesizer & n8n Workflow Packaging

### Output Formats Supported
1. **Markdown Tables**: Clean formatted tables ready for chat or documentation.
2. **CSV / Excel**: Standard structured data export.
3. **Executive Text Summaries**: High-level distilled takeaways with direct links.
4. **Mermaid Diagrams**: Visual flowcharts representing price distributions or group activity clusters.
5. **Action Dispatches**: Direct Telegram Bot messages or REST webhook notifications.

---

## 5. Execution Model: n8n Workflow & FastAPI Bridge Architecture

To decouple complex browser automation and AI SDK dependencies from n8n's workflow engine, the system uses a **FastAPI Microservice Bridge** pattern with a **Universal AI Output Synthesizer**.

### Comprehensive Component & Communication Block Diagram

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                              N8N ORCHESTRATION CANVAS (BOX 1)                                              │
│                                                                                                                            │
│   ┌───────────────────────────────┐               ┌───────────────────────────────┐                                        │
│   │ Node 1: User Input Trigger    │──────────────►│ Node 2: Input Normalizer      │                                        │
│   │ (n8n Webhook Node)            │  In-Memory JS │ (n8n Code Node)               │                                        │
│   └───────────────────────────────┘   Data Event  └───────────────────────────────┘                                        │
│                  ▲                                                │                                                        │
│                  │                                                │ In-Memory JS                                           │
│                  │ HTTP 200 JSON                                  ▼ Data Event                                             │
│                  │ (Final Output)                 ┌───────────────────────────────┐                                        │
│   ┌───────────────────────────────┐               │ Node 3: AI Task Compiler      │                                        │
│   │ Node 9: Return Response       │               │ (n8n HTTP Request Node)       │                                        │
│   │ (n8n Respond to Webhook Node) │               └───────────────────────────────┘                                        │
│   └───────────────────────────────┘                               │                                                        │
│         ▲                    ▲                                    │ HTTP POST /compile                                     │
│         │                    │                                    ▼                                                        │
│         │ In-Memory JS       │ In-Memory JS       ┌────────────────────────────────────────────────────────────────────┐   │
│         │ Data Event         │ Data Event         │ FASTAPI BRIDGE BACKEND (BOX 2) (src/n8n_bridge/server.py)          │   │
│   ┌─────────────┐      ┌─────────────┐            │                                                                    │   │
│   │ Node 8a: AI │      │ Node 8b:    │            │ ┌────────────────────────────────────────────────────────────────┐ │   │
│   │ Obstacle    │      │ Universal AI│            │ │ Google Gemini 2.5 Flash REST API                               │ │   │
│   │ Diagnostic  │      │ Synthesizer │            │ │ (https://generativelanguage.googleapis.com)                    │ │   │
│   │ (Code Node) │      │ (HTTP Node) │            │ │ • Protocol: HTTPS POST (GEMINI_API_KEY)                        │ │   │
│   └─────────────┘      └─────────────┘            │ │ • Compiler: NL Prompt -> Canonical TaskManifest JSON           │ │   │
│         ▲                    ▲                    │ │ • Vision: DOM Obstacle coordinates & interactive solving       │ │   │
│         │ Obstacle (0 posts) │ Success (>0 posts) │ │ • Universal Synthesizer: Arbitrary Output (HTML, XML, YAML...) │ │   │
│   ┌───────────────────────────────┐               │ └────────────────────────────────────────────────────────────────┘ │   │
│   │ Node 7: Scrape Result Router  │               │                          ▲                                         │   │
│   │ (n8n If Condition Node)       │               │                          │ HTTPS REST                              │   │
│   └───────────────────────────────┘               │                          ▼                                         │   │
│                  ▲                                │ ┌────────────────────────────────────────────────────────────────┐ │   │
│                  │ In-Memory JS Data              │ │ Playwright Chromium Stealth Engine                             │ │   │
│   ┌───────────────────────────────┐               │ │ • Protocol: Async CDP (Chrome DevTools Protocol)               │ │   │
│   │ Node 6: Playwright Scraper    │──────────────►│ │ • Session: session_storage.json cookie state                   │ │   │
│   │ (n8n HTTP Request Node)       │   HTTP POST   │ │ • Extraction: Accessibility Trees & Clean DOM Post Models      │ │   │
│   └───────────────────────────────┘   /scrape     │ └────────────────────────────────────────────────────────────────┘ │   │
│                  ▲                                │                          │                                         │   │
│                  │ Authenticated                  │                          ▼                                         │   │
│   ┌───────────────────────────────┐               │ ┌────────────────────────────────────────────────────────────────┐ │   │
│   │ Node 5: Is Authenticated?     │               │ │ Universal Output Synthesizer Engine                            │ │   │
│   │ (n8n If Node / Login Branch)  │               │ │ • High-speed Deterministic: CSV, Markdown, HTML Table, JSON    │ │   │
│   └───────────────────────────────┘               │ │ • Dynamic AI Synthesizer: XML, YAML, LaTeX, Custom Formats     │ │   │
│                  ▲                                │ └────────────────────────────────────────────────────────────────┘ │   │
│                  │ HTTP GET /session/status       │                                                                    │   │
│   ┌───────────────────────────────┐               │                                                                    │   │
│   │ Node 4: Check Session Status  │──────────────►│                                                                    │   │
│   │ (n8n HTTP Request Node)       │               │                                                                    │   │
│   └───────────────────────────────┘               └────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Universal AI Output Synthesizer Architecture:
Instead of requiring pre-configured formats in advance, the pipeline features a **Hybrid Synthesis Engine**:
1. **Deterministic Fast-Paths**: Standard formats (CSV, Markdown Tables, HTML Tables, JSON, Mermaid diagrams) are rendered directly in-process for millisecond response times.
2. **AI-Driven Dynamic Formatting**: When a user requests arbitrary or specialized formats (e.g., XML schemas, YAML configs, LaTeX documents, custom HTML templates, executive summaries, bullet points), the structured `PostPayload` objects and user instructions are routed to **Google Gemini 2.5 Flash**, synthesizing the exact requested format on the fly without workflow modifications.

### How the AI Model (Google Gemini) is Contacted in the Flow:
1. **Credentials**: The FastAPI bridge loads `GEMINI_API_KEY` and `GEMINI_MODEL=gemini-2.5-flash` from `.env` on startup.
2. **Task Compilation (`/compile`)**:
   - `TaskCompiler` (`src/compiler/task_compiler.py`) formats the user's prompt alongside `SYSTEM_COMPILER_PROMPT`.
   - Sends a REST request to `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}`.
   - Gemini returns structured JSON matching `TaskManifest`.
3. **Obstacle Solving (`/solve-obstacle`)**:
   - When Playwright encounters interactive obstacles (popups, "See more" buttons, login prompts), it captures a base64 screenshot crop.
   - `VisionFallbackHandler` (`src/scraper/vision_fallback.py`) calls Gemini Vision with `inline_data` to locate target click coordinates.
4. **Universal Output Synthesis (`/synthesize`)**:
   - `OutputSynthesizer` (`src/synthesizer/formatters.py`) dynamically routes custom/complex format requests to Gemini 2.5 Flash, generating clean, formatted outputs in any target dialect.

---

## 5. Directory & Package Structure

```
FacebookScraper/
├── .github/
│   ├── copilot-instructions.md          # Active CLI instructions
│   └── agents/                          # Specialized custom agent definitions
├── docs/
│   ├── ARCHITECTURE.md                  # This specification document
│   ├── PROJECT_ROADMAP.md               # Pinned milestone tracker
│   └── COPILOT_CLI_WORKFLOW_GUIDE.md    # CLI guide for subagents & forking
├── src/
│   ├── compiler/                        # Tier 1: Natural Language -> Manifest
│   │   ├── __init__.py
│   │   ├── task_compiler.py
│   │   └── prompt_templates.py
│   ├── scraper/                         # Tier 2: Resilient Browser Engine
│   │   ├── __init__.py
│   │   ├── browser_manager.py
│   │   ├── accessibility_parser.py
│   │   ├── obstacle_handler.py
│   │   └── post_extractor.py
│   ├── synthesizer/                     # Tier 3: Formatting & Output Engine
│   │   ├── __init__.py
│   │   ├── table_formatter.py
│   │   ├── csv_formatter.py
│   │   ├── summary_formatter.py
│   │   └── diagram_formatter.py
│   ├── models/                          # Pydantic / Typed Data Contracts
│   │   ├── __init__.py
│   │   ├── manifest.py
│   │   └── post.py
│   └── n8n_bridge/                      # HTTP Webhook API for n8n integration
│       ├── __init__.py
│       └── app.py
├── tests/                               # TDD Unit & Integration Test Suite
│   ├── test_task_compiler.py
│   ├── test_accessibility_parser.py
│   ├── test_obstacle_handler.py
│   ├── test_synthesizer.py
│   └── fixtures/                        # HTML snapshots and mock payloads
├── workflows/                           # Exportable n8n workflow JSONs
│   └── facebook_scraper_master.json
├── requirements.txt
└── README.md
```

---

## 6. Development Milestones & TDD Flow

1. **Step 1 (Models & Contracts)**: Define Pydantic models for `TaskManifest` and `PostPayload`.
2. **Step 2 (Task Compiler TDD)**: Write failing tests (`tests/test_task_compiler.py`) for various human prompts $\rightarrow$ Implement `task_compiler.py` until tests pass.
3. **Step 3 (Synthesizer TDD)**: Write failing tests (`tests/test_synthesizer.py`) for table, CSV, and diagram generation $\rightarrow$ Implement formatters until green.
4. **Step 4 (Scraper & Parser TDD)**: Write mock DOM tests for Accessibility parsing and obstacle dismissal $\rightarrow$ Implement Playwright driver.
5. **Step 5 (n8n Packaging)**: Expose Fast API bridge and construct importable n8n JSON workflow.
