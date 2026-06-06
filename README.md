```markdown
# Code Review Agent (Local Pre-Push Reviewer)

A lightweight, local command-line tool designed to analyze code changes and provide structured suggestions before code is pushed to remote branches. By executing locally, the tool catches potential logical errors, security risks, and performance problems early in the development lifecycle, keeping feedback loops fast and local.

Unlike typical static analysis tools or single-prompt LLM wrappers, this system relies on a multi-stage, agentic workflow that extracts structural context from your source files before submitting them for review.

---

## Key Features

*   **Context-Aware Analysis:** Resolves modified lines back to their enclosing function or class using Python's Abstract Syntax Trees (AST) or a local sliding window.
*   **Parallel Multi-Perspective Auditing:** Runs separate Critic Agents concurrently to inspect logic, security vulnerabilities (such as leaked tokens or injection vectors), and performance constraints.
*   **Consolidated Feedback (Synthesis Agent):** Merges conflicting critiques, filters out minor/pedantic noise, and generates standard markdown inline ````suggestion```` blocks.
*   **Frictionless Git Integration:** Automatically analyzes unpushed changes via a non-intrusive pre-push hook. It outputs suggestions directly to your terminal without blocking your git workflow or preventing pushes.

---

## Directory Structure

Ensure your project contains the following layout inside the `code-review-agent/` directory:

```text
code-review-agent/
├── requirements.txt      # Project dependencies
├── config.py            # Global configuration settings and file filters
├── git_utils.py         # Git diff parser and modified line detector
├── context_retriever.py # AST parser & sliding-window fallback context extractor
├── agent_engine.py      # Multi-agent coordinator and critic definitions
├── synthesis_agent.py   # Final review editor and suggestion formatter
├── install_hook.py      # Automation script to install Git hooks
└── main.py              # CLI entry point
```

---

## Setup & Installation

### 1. Install Dependencies
Run the following command inside your environment to install the required packages:

```bash
pip install -r code-review-agent/requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory of your repository. Provide your API key and preferred model configurations:

```env
OPENAI_API_KEY=your_actual_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_API_BASE=https://api.openai.com/v1
```

---

## Usage

### Automated Pre-Push Check (Recommended)
You can automate the review agent to evaluate changes whenever you run `git push`. To install the non-blocking Git hook, execute:

```bash
python code-review-agent/install_hook.py
```

*Note: The generated pre-push hook is designed to prioritize local virtual environments (`.venv` or `venv`) to prevent python import issues when executed via external Git clients.*

### Manual Check
To manually trigger a codebase analysis on your unpushed commits without attempting a push, run:

```bash
python code-review-agent/main.py analyze
```

#### Optional CLI Arguments
*   `--repo-path`: Specifies the path to the target Git repository (defaults to current directory `.`):
    ```bash
    python code-review-agent/main.py analyze --repo-path /path/to/repo
    ```

---

## Technical Architecture

1.  **Diff Filtering:** `git_utils.py` queries Git to find modified files in the local branch that have not yet been pushed upstream. Configured extension filters ignore heavy or irrelevant files (e.g., lockfiles, graphics).
2.  **Context Extraction:** `context_retriever.py` parses modified files. For Python code, it uses AST walking to locate and extract the full body of any function containing edited lines. Other formats default to a line-neighborhood search window.
3.  **Audit Execution:** `agent_engine.py` initiates an asynchronous gather event, sending the gathered context and raw diff to separate specialized critic instructions in parallel.
4.  **Review Synthesis:** `synthesis_agent.py` combines the draft observations. If no structural failures remain, it yields `APPROVED`. Otherwise, it outputs a consolidated critique complete with inline suggestions.
```