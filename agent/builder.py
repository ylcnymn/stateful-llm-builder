Here are the key parts of your code with concise English inline comments explaining their purpose:

```python
import json
import subprocess
import os
from pathlib import Path
from datetime import datetime
import re

# Project directory structure
BASE = Path(__file__).resolve().parents[1]  # Root of the project
AGENT = BASE / "agent"                      # Directory containing agent logic
OUTPUT = BASE / "output"                    # Whitelisted output directory
LOGS = BASE / "logs"                        # Directory for run logs

# Ensure required directories exist
OUTPUT.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)

# Use environment variable for model selection, fallback to default
MODEL = os.getenv("BUILDER_MODEL", "qwen3-coder:480b-cloud")


def read_file(path: Path) -> str:
    """Read a file; raise error if missing."""
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return path.read_text(encoding="utf-8")


def call_ollama(prompt: str) -> str:
    """Invoke Ollama with the given prompt and return its output."""
    env = os.environ.copy()
    env["LANG"] = "C.UTF-8"  # Ensure consistent UTF-8 encoding
    result = subprocess.run(
        ["ollama", "run", MODEL],
        input=prompt,
        text=True,
        encoding="utf-8",
        capture_output=True,
        env=env,
    )
    # Raise error if Ollama fails
    if result.returncode != 0:
        raise RuntimeError(
            f"Ollama failed with code {result.returncode}:\n"
            f"STDERR: {result.stderr}\nSTDOUT: {result.stdout}"
        )
    return result.stdout


def build_prompt() -> str:
    """Construct the full prompt by combining all context files."""
    return f"""
{read_file(AGENT / "prompt.txt")}

--- project.md ---
{read_file(BASE / "project.md")}

--- rules.json ---
{read_file(BASE / "rules.json")}

--- progress.json ---
{read_file(BASE / "progress.json")}
""".strip()


# Regex to parse LLM output into file blocks
FILE_BLOCK_RE = re.compile(
    r"--- file: (?P<path>.+?) ---\n(?P<content>.*?)(?=\n--- file: |\Z)",
    re.DOTALL
)


def clean_llm_output(raw: str) -> str:
    """Remove trailing standalone '---' lines that are not part of a file block."""
    lines = raw.splitlines()
    while lines and lines[-1].strip() == "---":
        lines.pop()
    return "\n".join(lines)


def parse_files(llm_output: str):
    """Extract valid file blocks from LLM output."""
    blocks = []
    for match in FILE_BLOCK_RE.finditer(llm_output):
        rel_path = match.group("path").strip()
        content = match.group("content").rstrip()

        # Skip empty content
        if not content.strip():
            continue

        # Block unsafe paths (directory traversal, absolute paths, Windows drives)
        if ".." in rel_path or rel_path.startswith("/") or ":" in rel_path:
            print(f"Skipped unsafe path: {rel_path}")
            continue

        blocks.append((rel_path, content))
    return blocks


def write_files(file_blocks):
    """Write parsed files only to allowed locations."""
    written = []
    for rel_path, content in file_blocks:
        target = BASE / rel_path

        # Enforce strict write whitelist: only output/ and progress.json
        if not (
            rel_path.startswith("output/")
            or rel_path == "progress.json"
        ):
            print(f"Skipped unauthorized path: {rel_path}")
            continue

        # Create parent directories if needed
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(rel_path)

    return written


def log_run(text: str):
    """Append raw output or error to the run log with timestamp."""
    with open(LOGS / "run.log", "a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.now()}]\n{text}\n")


def main():
    """Orchestrate one agent step: prompt → LLM → parse → write → log."""
    prompt = build_prompt()
    try:
        raw_output = call_ollama(prompt)
        cleaned_output = clean_llm_output(raw_output)
    except Exception as e:
        log_run(f"ERROR: {e}")
        raise

    log_run(cleaned_output)

    file_blocks = parse_files(cleaned_output)

    if not file_blocks:
        print("No files to write. Agent did nothing.")
        return

    written = write_files(file_blocks)

    print("Written files:")
    for w in written:
        print(" -", w)


if __name__ == "__main__":
    main()
```
