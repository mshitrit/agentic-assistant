from pathlib import Path
from config.settings import SBR_REPO_PATH

LIVING_MEMORY_DIR = Path(__file__).parent.parent / "memory" / "living"


def _repo_root() -> Path | None:
    if not SBR_REPO_PATH:
        return None
    path = Path(SBR_REPO_PATH)
    return path if path.is_dir() else None


def read_file(file_path: str) -> str:
    root = _repo_root()
    if root is None:
        return "Error: SBR_REPO_PATH is not configured or does not exist."
    full_path = (root / file_path).resolve()
    if not str(full_path).startswith(str(root)):
        return "Error: path traversal outside repo root is not allowed."
    if not full_path.is_file():
        return f"Error: file not found: {file_path}"
    return full_path.read_text()


def list_directory(dir_path: str = "") -> str:
    root = _repo_root()
    if root is None:
        return "Error: SBR_REPO_PATH is not configured or does not exist."
    full_path = (root / dir_path).resolve()
    if not str(full_path).startswith(str(root)):
        return "Error: path traversal outside repo root is not allowed."
    if not full_path.is_dir():
        return f"Error: directory not found: {dir_path}"
    entries = sorted(full_path.iterdir())
    lines = [("DIR  " if e.is_dir() else "FILE ") + e.name for e in entries]
    return "\n".join(lines)


def write_memory_file(filename: str, content: str) -> str:
    full_path = (LIVING_MEMORY_DIR / filename).resolve()
    if not str(full_path).startswith(str(LIVING_MEMORY_DIR.resolve())):
        return "Error: path traversal outside living memory directory is not allowed."
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content)
    print(f"[MEMORY UPDATE] Living memory updated: {filename}")
    return f"Successfully updated living memory: {filename}"


# Tool definitions in Anthropic tool-use format (used in Step 7)
TOOL_DEFINITIONS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file from the SBR repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file relative to the repo root (e.g. 'cmd/sbr-agent/main.go')"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "list_directory",
        "description": "List files and subdirectories in a directory of the SBR repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dir_path": {
                    "type": "string",
                    "description": "Path to the directory relative to the repo root. Leave empty for the root."
                }
            },
            "required": []
        }
    },
    {
        "name": "write_memory_file",
        "description": (
            "Update a file in living memory when you detect that the current SBR codebase "
            "contradicts your verified domain knowledge. Only call this after directly "
            "verifying the discrepancy in source code — do not speculate."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Path relative to memory/living/ (e.g. 'sbr/architecture.md')"
                },
                "content": {
                    "type": "string",
                    "description": "Full updated content for the memory file"
                }
            },
            "required": ["filename", "content"]
        }
    }
]
