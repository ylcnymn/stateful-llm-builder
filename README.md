# stateful-llm-builder

A small experimental project that demonstrates a state-driven LLM agent which incrementally builds a frontend application using a local Ollama model.

This repository is intended as a controlled research/learning environment — it shows one practical way to turn an LLM from a one-shot code generator into a cautious, state-aware development assistant.

---

## Table of contents

- What is this repository for?
- What this project intentionally does NOT do
- Requirements
- How to run
- What the project actually does
- Core idea
- High-level architecture
- The role of `builder.py`
- Step-by-step execution flow
- Safety, idempotency and logging
- Notes and caveats

---

## What is this repository for?

This repo explores several questions at the intersection of LLMs and software engineering:

- Can an LLM build software step-by-step while remembering previous work?
- How should prompts, explicit file-state, and code interact to keep the process safe and repeatable?
- What minimal architecture is required so the model produces one well-defined change per run?

In short: it’s an experiment in turning an LLM into a disciplined, file-backed agent that incrementally constructs a frontend project.

---

## What this project intentionally does NOT do

This is focused research; some hard problems are out of scope on purpose:

- Automatic, broad-scope refactoring (dangerous without complete context)
- Diff-first code analysis or arbitrary in-place edits
- Automated test generation
- Multi-agent coordination or decentralized orchestration

Those are interesting follow-ups, but intentionally excluded here.

---

## Requirements

- Python 3.10+
- Ollama installed and running locally
- A local Ollama model accessible to your Ollama instance (tested with qwen3-coder variants)

---

## How to run

Start your Ollama service and ensure the chosen model is available, then run:

```bash
python agent/builder.py
```

The agent will read the repository state, ask the local model to perform a single next step, and apply only allowed changes.

---

## What does this project do?

This repository implements an autonomous-but-controlled agent that:

- Uses a local LLM (via Ollama) to produce a single next task output per run
- Stores and drives progress entirely from files (no hidden memory)
- Writes only to whitelisted paths and only when explicitly permitted
- Logs every run so results can be inspected and reproduced

Unlike demos that regenerate an entire project at once, this system proceeds incrementally and deterministically, making it safe to run repeatedly.

---

## Core idea

Can an LLM build software step-by-step while remembering what it already did, instead of trying to generate everything at once?

This project demonstrates that yes — but only when you combine a clear state representation, strict agent prompts, and guarded parsing/writing logic.

---

## High-level architecture

Files that drive the system:

- `progress.json` — what has been done and what comes next
- `project.md` — human-readable description of the project being built
- `rules.json` — technical and stylistic constraints the agent must follow
- `prompt.txt` — agent behavior and instruction template

Controller:

- `agent/builder.py` — reads state, calls the LLM, parses output, writes allowed files

Output:

- `output/` — generated frontend files (whitelisted)

The system is file-driven: the files listed above are the only truth the agent uses when deciding what to do next.

---

## The role of `builder.py`

`builder.py` is the orchestrator and enforcer. Its job is strict:

What it does NOT do:
- Never gives the model free rein to modify arbitrary project files
- Does not regenerate the full project on every run
- Does not accept arbitrary paths or unstructured outputs

What it DOES do:
- Loads the state files (`project.md`, `rules.json`, `progress.json`)
- Asks the LLM to perform exactly one next task (based on `progress.json.next`)
- Parses the LLM’s reply using well-defined, parsable file-blocks
- Accepts and writes only whitelisted paths (`output/*` and `progress.json`)
- Updates `progress.json` and saves logs for each run

---

## Step-by-step execution flow

1. Read the current state:
   - `project.md` — project description
   - `rules.json` — constraints and style rules
   - `progress.json` — what’s been completed and the next task

2. Instruct the LLM to perform exactly one next task:
   - The agent enforces: “Do only the task defined in `progress.json.next`. Do not repeat or change previous steps.”

3. LLM replies using explicit file blocks. Example expected format:

```text
--- file: output/style.css ---
/* CSS content here */
body { font-family: system-ui, sans-serif; }

--- file: progress.json ---
{
  "completed": ["init"],
  "next": "add-basic-layout"
}
```

4. `builder.py`:
   - Parses the blocks
   - Validates paths against the whitelist
   - Writes allowed files (never arbitrary system files)
   - Updates `progress.json` accordingly
   - Logs raw model output and decisions for auditing

---

## Safety, controlled writing and idempotency

- Only whitelisted paths are writable: `output/*` and `progress.json`.
- Existing files are not overwritten blindly — the agent controls what to create/update.
- Unauthorized file writes are ignored to prevent accidental damage.
- The system is designed to be idempotent: if `progress.json.next` is `"done"`, the agent writes nothing and exits quietly.
- You can run the agent repeatedly (even from cron) without cumulative risk: running it 10 times won’t break things 10 times.

Example of a terminal "done" state in `progress.json`:

```json
{
  "completed": ["init", "add-basic-layout", "style"],
  "next": "done"
}
```

---

## Logging and inspection

Every run stores:
- Raw LLM output
- The parsed decisions (which blocks were accepted/rejected)
- The resulting state and any file writes

This makes runs reproducible and easy to audit for research or debugging.

---

## Notes and caveats

- This is research code, not production software. It’s intentionally conservative.
- The approach trades breadth of automation for safety, repeatability and interpretability.
- If you want to expand this system (tests, refactorers, multi-agent coordination), treat those as distinct next-step experiments and add rigorous safeguards.

---

If you want, I can:
- Polish or translate `project.md`, `rules.json`, or example `progress.json` to be clearer,
- Add a minimal example project in `output/` so the agent has a concrete first task,
- Or prepare a short tutorial showing a sample run and its logs.

License: none specified — add one if you intend to share or reuse this project publicly.
