# locic-

A Python-based experimental workflow repository for automated code generation, review, and refinement.

## Key scripts

- `WorkflowOrchestratorv2.py` - main CLI workflow driver. Pass a task description to generate, review, and save code.
- `chatbot.py` - simple local chatbot with persistent conversation memory.
- `Implement guardrails.py` - optional workflow runner that reads guardrail settings from `config.yaml`.
- `The Consolidated Pipeline.py` / `The Orchestrator.py` - alternate orchestrator versions in the top-level repo.

## Getting started

Install minimal dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Install the package locally:

```bash
python3 -m pip install -e .
```

Run the workflow orchestrator:

```bash
python3 WorkflowOrchestratorv2.py "Generate a Python utility that prints system info"
```

Run the repository launcher:

```bash
python3 run.py workflow "Generate a Python utility that prints system info"
python3 run.py chatbot
python3 run.py test
```

Run the chatbot:

```bash
python3 chatbot.py
```

## Configuration

`config.yaml` contains optional guardrail settings used by `Implement guardrails.py`.

## Notes

- This repository is intentionally lightweight and experimental.
- Generated outputs are written to `workshop_dir/`.
- Conversation history is stored in `chat_memory/`.
- A top-level `AGENTS.md` file exists for AI agent instructions and repository context.

