import json
import subprocess
from pathlib import Path
from datetime import datetime
import re

BASE = Path(__file__).resolve().parents[1]
AGENT = BASE / "agent"
OUTPUT = BASE / "output"
LOGS = BASE / "logs"

OUTPUT.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)

MODEL = "qwen3-coder:480b-cloud"


def read_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing file: {path}")
    return path.read_text(encoding="utf-8")


def call_ollama(prompt: str) -> str:
    result = subprocess.run(
        ["ollama", "run", MODEL],
        input=prompt,
        text=True,
        encoding="utf-8",
        capture_output=True
    )
    return result.stdout


def build_prompt() -> str:
    return f"""
{read_file(AGENT / "prompt.txt")}

--- project.md ---
{read_file(BASE / "project.md")}

--- rules.json ---
{read_file(BASE / "rules.json")}

--- progress.json ---
{read_file(BASE / "progress.json")}
""".strip()


FILE_BLOCK_RE = re.compile(
    r"--- file: (?P<path>.+?) ---\n(?P<content>.*?)(?=\n--- file: |\Z)",
    re.DOTALL
)


def parse_files(llm_output: str):
    return [
        (match.group("path").strip(), match.group("content").rstrip())
        for match in FILE_BLOCK_RE.finditer(llm_output)
    ]


def write_files(file_blocks):
    written = []
    for rel_path, content in file_blocks:
        target = BASE / rel_path

        if not (
            rel_path.startswith("output/")
            or rel_path == "progress.json"
        ):
            print(f"Skipped unauthorized path: {rel_path}")
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(rel_path)

    return written


def log_run(text: str):
    with open(LOGS / "run.log", "a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.now()}]\n{text}\n")


def main():
    prompt = build_prompt()
    llm_output = call_ollama(prompt)

    log_run(llm_output)

    file_blocks = parse_files(llm_output)

    if not file_blocks:
        print("No files to write. Agent did nothing.")
        return

    written = write_files(file_blocks)

    print("Written files:")
    for w in written:
        print(" -", w)


if __name__ == "__main__":
    main()
