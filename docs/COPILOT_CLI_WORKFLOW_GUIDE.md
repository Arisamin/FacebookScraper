# Copilot CLI Advanced Capabilities Guide
> **Hands-On Tutorial**: Subagents, Session Forking, and Custom Agent Roles  
> Project: `FacebookScraper` (`c:\MyData\Git\FacebookScraper`)

---

## 1. Subagents & Background Research Agents

### What is a Subagent?
A **subagent** is an isolated worker agent spawned in its own context window with a dedicated toolset (e.g., `research`, `explore`, `task`, `code-review`).

### Benefits
- **Zero Context Clutter**: Lengthy web pages, test logs, or large files read by the subagent do **not** consume your main conversation's token window.
- **Parallel Work**: A subagent can run in the background while you continue planning or editing code.

---

### Scenario A: Launching a Research Subagent

#### What to type in your prompt:
Simply ask Copilot in natural language:
> *"Launch a background research agent to inspect n8n's latest AI Agent node webhooks and Playwright HTTP wrapper architecture."*

#### What happens under the hood:
1. Copilot calls the `task` tool with `agent_type: "research"` and `mode: "background"`.
2. The subagent starts running in an independent background subprocess.
3. You will see an on-screen indicator (e.g., `Agent research-n8n-worker running...`).

#### What happens in your main session in the meantime:
- **You are NOT blocked.** You can continue asking questions, writing code, or running tests.
- Alternatively, you can press **`Ctrl+X → b`** on long operations to push them to the background.

#### How you get the subagent's output:
- When the subagent finishes, a **completion notification** automatically arrives in your session.
- Copilot reads the output via `read_agent` and summarizes the findings directly into your conversation.
- You can manually inspect background jobs at any time by typing:
  ```
  /tasks
  ```

---

## 2. Session Forking (`/fork`) & Session Switching (`/resume`)

### What is Session Forking?
Session forking creates a snapshot clone of your entire conversation history at a specific point in time, allowing you to explore alternative experiments without modifying or polluting your main branch.

```
Main Session (FacebookScraper Dev)
   │
   ├── Turn 1: Design Review
   ├── Turn 2: Architecture Discussion
   └── [ /fork n8n-docker-experiment ]
             │
             └──► Branch Session (n8n-docker-experiment)
                     └── Test Docker / n8n setups
```

---

### Step-by-Step Forking Workflow

#### Step 1: Fork the session
In the CLI prompt, type:
```
/fork n8n-docker-experiment
```
*Copilot clones the timeline and immediately switches you into the new session `n8n-docker-experiment`.*

#### Step 2: Work inside the forked session
Run your experimental prompts, tests, or subagents.

#### Step 3: View available sessions
To see your previous sessions and their IDs:
```
/session
```
or
```
/resume
```
*This displays an interactive menu listing all saved sessions, their names, and timestamps.*

#### Step 4: Switch back to the main session
Type:
```
/resume
```
and select your original session from the list (or pass its name/ID, e.g. `/resume main`).

---

### What happens if a subagent is running when you switch sessions?
1. **Background Isolation**: The subagent continues running in its own subprocess attached to the session that launched it.
2. **Resuming Later**: When you switch back (`/resume`), any completed agent results or notifications will be waiting for you to review.

---

## 3. Custom Agent Definitions (`.github/agents/`)

You can create permanent, specialized subagents for your repository by defining Markdown files inside `.github/agents/`.

### Example: `.github/agents/task-compiler.agent.md`
```markdown
---
name: task-compiler
description: Specializes in converting human natural language scraping requests into structured JSON manifests.
tools: ["view", "edit", "create", "grep"]
model: "gemini-3.7-flash"
---

You are the Task Compiler Specialist for FacebookScraper.
Your sole responsibility is parsing natural language instructions into validated JSON schemas.
```

### How to use a Custom Agent:
In the CLI:
1. Type **`/agent`** to browse available agents.
2. Type **`/agent task-compiler`** to switch into that specialist's context.

---

## 4. Quick Command Summary Cheatsheet

| Command | Action |
|---|---|
| `/fork <name>` | Clone current conversation into a new experimental branch session |
| `/resume` | List all sessions and switch between them |
| `/tasks` | View active background subagents and shell processes |
| `Ctrl+X → b` | Move the currently running command/agent to the background |
| `/agent` | Browse and select specialized custom agents |
| `/context` | Check how many tokens your current window is using |
| `/usage` | Display credit usage and token statistics |
