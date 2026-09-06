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
