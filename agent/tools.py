from pathlib import Path

LIVING_MEMORY_DIR = Path(__file__).parent.parent / "memory" / "living"


def _resolve_repo_root(repo_path: str) -> Path | None:
    if not repo_path:
        return None
    path = Path(repo_path)
    return path if path.is_dir() else None


def read_file(file_path: str, repo_path: str = "") -> str:
    root = _resolve_repo_root(repo_path)
    if root is None:
        return "Error: repo path is not configured or does not exist."
    full_path = (root / file_path).resolve()
    if not str(full_path).startswith(str(root)):
        return "Error: path traversal outside repo root is not allowed."
    if not full_path.is_file():
        return f"Error: file not found: {file_path}"
    return full_path.read_text()


def list_directory(dir_path: str = "", repo_path: str = "") -> str:
    root = _resolve_repo_root(repo_path)
    if root is None:
        return "Error: repo path is not configured or does not exist."
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


TOOL_DEFINITIONS = [
    {
        "name": "read_file",
        "description": "Read the contents of a file from the operator repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file relative to the repo root (e.g. 'cmd/agent/main.go')"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "list_directory",
        "description": "List files and subdirectories in a directory of the operator repository.",
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
            "Update a file in living memory when you detect that the current operator codebase "
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
