from pathlib import Path
from config.settings import SBR_REPO_PATH


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


# Tool definitions in Anthropic tool-use format (used in Step 6)
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
    }
]
