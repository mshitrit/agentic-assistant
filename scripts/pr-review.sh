#!/usr/bin/env bash
# Review a GitHub pull request or GitLab merge request from its URL.
# Fetches metadata and the platform diff via gh / glab (no local checkout).
#
# Usage:
#   scripts/pr-review.sh <PR_OR_MR_URL> [-o FILE] [-p] [--login] [--install-deps]
#   scripts/pr-review.sh auth <github|HOST|PR_OR_MR_URL>
#   scripts/pr-review.sh setup [github|gitlab|all|PR_OR_MR_URL]
#
# Examples:
#   ./scripts/pr-review.sh https://github.com/medik8s/fence-agents-remediation/pull/87
#   ./scripts/pr-review.sh https://gitlab.cee.redhat.com/dragonfly/machine-deletion-remediation/-/merge_requests/473
#
# Requires (per platform): gh (GitHub), glab + jq (GitLab)
# Auth: gh auth login / glab auth login — or set GH_TOKEN / GLAB_TOKEN (read by gh/glab, not set by this script)
# Vertex: config/config.txt (GCP_PROJECT_ID, GCP_REGION) + python -m agent.pr_review
#         gcloud auth application-default login
#
# Environment:
#   PR_REVIEW_MAX_BYTES      Truncate diff (default: 400000)
#   PR_REVIEW_PROMPT_FILE    Override review rubric (default: agent/prompts.py)
#   PR_REVIEW_LLM_CMD        Override LLM (reads prompt on stdin)
#   PR_REVIEW_CONTEXT_FILE   Extra markdown appended to the prompt
#   PR_REVIEW_INSTALL_DEPS   Set to 1 to auto-install missing CLIs (same as --install-deps)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAX_BYTES="${PR_REVIEW_MAX_BYTES:-400000}"
INSTALL_DEPS="${PR_REVIEW_INSTALL_DEPS:-0}"

OUT=""
PRINT_PROMPT=0
FORCE_LOGIN=0
URL=""

usage() {
  cat <<'EOF'
Review a GitHub pull request or GitLab merge request from its URL.
Fetches metadata and the platform diff via gh / glab (no local checkout).

Usage:
  scripts/pr-review.sh <PR_OR_MR_URL> [-o FILE] [-p] [--login] [--install-deps]
  scripts/pr-review.sh auth <github|HOST|PR_OR_MR_URL>
  scripts/pr-review.sh setup [github|gitlab|all|PR_OR_MR_URL]

Examples:
  ./scripts/pr-review.sh https://github.com/medik8s/fence-agents-remediation/pull/87
  ./scripts/pr-review.sh https://gitlab.cee.redhat.com/dragonfly/machine-deletion-remediation/-/merge_requests/473

Requires (per URL): gh (GitHub), glab + jq (GitLab)

Options:
  -o, --out FILE       Write LLM review to FILE (stdout if omitted)
  -p, --prompt         Print the assembled prompt only (no LLM call)
  --login              Force interactive auth login before fetching
  --install-deps       Install missing gh/glab/jq via system package manager (may use sudo)
  -h, --help           Show this help

Auth: gh auth login / glab auth login --hostname HOST
      Non-interactive: GH_TOKEN (GitHub) or GLAB_TOKEN (GitLab), read by gh/glab
      Run: ./scripts/pr-review.sh auth <github|HOST|URL>

Install CLIs: ./scripts/pr-review.sh setup [github|gitlab|all]

Review: Claude via Vertex (config/config.txt). Fallback: PR_REVIEW_LLM_CMD, cursor, claude CLI.
EOF
}

install_gh() {
  command -v gh &>/dev/null && return 0
  echo "pr-review: installing gh..." >&2
  if command -v dnf &>/dev/null; then
    sudo dnf install -y gh
  elif command -v apt-get &>/dev/null; then
    sudo apt-get update -qq && sudo apt-get install -y gh
  elif command -v brew &>/dev/null; then
    brew install gh
  else
    die "cannot install gh automatically; see https://cli.github.com/"
  fi
}

install_glab() {
  command -v glab &>/dev/null && return 0
  echo "pr-review: installing glab..." >&2
  if command -v dnf &>/dev/null; then
    sudo dnf install -y glab
  elif command -v apt-get &>/dev/null; then
    sudo apt-get update -qq && sudo apt-get install -y glab
  elif command -v brew &>/dev/null; then
    brew install glab
  else
    die "cannot install glab automatically; see https://gitlab.com/gitlab-org/cli"
  fi
}

install_jq() {
  command -v jq &>/dev/null && return 0
  echo "pr-review: installing jq..." >&2
  if command -v dnf &>/dev/null; then
    sudo dnf install -y jq
  elif command -v apt-get &>/dev/null; then
    sudo apt-get update -qq && sudo apt-get install -y jq
  elif command -v brew &>/dev/null; then
    brew install jq
  else
    die "cannot install jq automatically"
  fi
}

ensure_cmd() {
  local cmd="$1" purpose="$2" installer="${3:-}"
  if command -v "$cmd" &>/dev/null; then
    return 0
  fi
  if [[ "$INSTALL_DEPS" == 1 && -n "$installer" ]]; then
    "$installer" || die "failed to install $cmd (required for $purpose)"
    command -v "$cmd" &>/dev/null \
      || die "'$cmd' not in PATH after install (required for $purpose)"
    return 0
  fi
  die "'$cmd' not found (required for $purpose). Install manually, run: $0 setup, or re-run with --install-deps"
}

ensure_github_deps() {
  ensure_cmd gh GitHub install_gh
}

ensure_gitlab_deps() {
  ensure_cmd glab GitLab install_glab
  ensure_cmd jq GitLab install_jq
}

ensure_provider_deps() {
  case "${PROVIDER:-}" in
    github) ensure_github_deps ;;
    gitlab) ensure_gitlab_deps ;;
    *) die "internal error: unknown provider for deps" ;;
  esac
}

find_python() {
  if command -v python3.11 &>/dev/null; then
    echo python3.11
  elif command -v python3 &>/dev/null; then
    echo python3
  else
    echo ""
  fi
}

die() {
  echo "pr-review: $*" >&2
  exit 1
}

is_tty() {
  [[ -t 0 && -t 1 ]]
}

is_gitlab_unauthorized() {
  local msg="$1"
  [[ "$msg" == *401* || "$msg" == *Unauthorized* || "$msg" == *Unauthenticated* ]]
}

gitlab_do_login() {
  local reason="${1:-}"
  ensure_cmd glab GitLab install_glab
  export GITLAB_HOST="$GITLAB_HOST"
  export GL_HOST="$GITLAB_HOST"
  [[ -n "$reason" ]] && echo "pr-review: $reason" >&2
  echo "pr-review: starting GitLab login for $GITLAB_HOST..." >&2
  glab auth login --hostname "$GITLAB_HOST" || die "GitLab login failed for $GITLAB_HOST"
  glab auth status -h "$GITLAB_HOST" &>/dev/null \
    || die "GitLab login did not complete for $GITLAB_HOST"
}

gitlab_project_encoded() {
  echo -n "$1" | sed 's|/|%2F|g'
}

github_ensure_auth() {
  ensure_github_deps
  if [[ "$FORCE_LOGIN" != 1 ]] && gh auth status &>/dev/null; then
    return 0
  fi
  if ! is_tty; then
    die "not logged in to GitHub. Run: $0 auth github (or set GH_TOKEN)"
  fi
  if [[ "$FORCE_LOGIN" == 1 ]]; then
    echo "pr-review: forcing GitHub login..." >&2
  else
    echo "pr-review: not logged in to GitHub. Starting interactive login..." >&2
  fi
  gh auth login || die "GitHub login failed"
  gh auth status &>/dev/null || die "GitHub login did not complete"
}

gitlab_ensure_auth() {
  ensure_gitlab_deps
  export GITLAB_HOST="$GITLAB_HOST"
  export GL_HOST="$GITLAB_HOST"

  if [[ "$FORCE_LOGIN" != 1 ]] && glab auth status -h "$GITLAB_HOST" &>/dev/null; then
    return 0
  fi
  if ! is_tty; then
    die "not logged in to $GITLAB_HOST. Run: $0 auth $GITLAB_HOST (or set GLAB_TOKEN)"
  fi
  if [[ "$FORCE_LOGIN" == 1 ]]; then
    gitlab_do_login "login requested (--login)"
  else
    gitlab_do_login "not logged in to $GITLAB_HOST"
  fi
}

gitlab_fetch_diff() {
  local err_file diff_err enc changes_json attempt=0
  err_file="$(mktemp)"

  while [[ "$attempt" -lt 2 ]]; do
    if DIFF="$(glab mr diff "$MR_IID" -R "$GITLAB_PROJECT" 2>"$err_file")"; then
      rm -f "$err_file"
      [[ -n "$DIFF" ]] || die "glab mr diff returned empty diff for !${MR_IID}"
      return 0
    fi

    diff_err="$(cat "$err_file")"
    if is_gitlab_unauthorized "$diff_err" && is_tty && [[ "$attempt" -eq 0 ]]; then
      : >"$err_file"
      attempt=1
      gitlab_do_login "GitLab token cannot read MR diffs (401)"
      continue
    fi
    break
  done

  echo "pr-review: glab mr diff failed; trying API /changes fallback..." >&2
  if is_gitlab_unauthorized "$diff_err"; then
    echo "pr-review: hint: re-login with api/read_api scope: glab auth login --hostname $GITLAB_HOST" >&2
  fi

  if ! command -v jq >/dev/null 2>&1; then
    echo "pr-review: ${diff_err}" >&2
    rm -f "$err_file"
    die "glab mr diff failed and jq is required for /changes fallback"
  fi

  enc="$(gitlab_project_encoded "$GITLAB_PROJECT")"
  attempt=0
  while [[ "$attempt" -lt 2 ]]; do
    if changes_json="$(glab api "projects/${enc}/merge_requests/${MR_IID}/changes" 2>"$err_file")"; then
      rm -f "$err_file"
      DIFF="$(printf '%s' "$changes_json" | jq -r '.changes[]? | .diff // empty')"
      if [[ -z "$DIFF" ]]; then
        die "MR changes API returned no diffs for !${MR_IID}"
      fi
      return 0
    fi

    diff_err="$(cat "$err_file")"
    if is_gitlab_unauthorized "$diff_err" && is_tty && [[ "$attempt" -eq 0 ]]; then
      : >"$err_file"
      attempt=1
      gitlab_do_login "GitLab token cannot read MR changes (401)"
      continue
    fi

    echo "pr-review: ${diff_err}" >&2
    cat "$err_file" >&2 || true
    rm -f "$err_file"
    die "could not fetch MR diff for $GITLAB_HOST/$GITLAB_PROJECT!${MR_IID}"
  done
}

cmd_setup() {
  local target="${1:-all}"
  INSTALL_DEPS=1
  case "$target" in
    github)
      install_gh
      ;;
    gitlab)
      install_glab
      install_jq
      ;;
    all)
      install_gh
      install_glab
      install_jq
      ;;
    *)
      if parse_url "$target"; then
        ensure_provider_deps
      else
        die "usage: $0 setup [github|gitlab|all|PR_OR_MR_URL]"
      fi
      ;;
  esac
  echo "pr-review: setup complete." >&2
}

cmd_auth() {
  local target="${1:-}"
  [[ -n "$target" ]] || die "usage: $0 auth <github|HOST|PR_OR_MR_URL>"

  if [[ "$target" == "github" ]]; then
    FORCE_LOGIN=1
    github_ensure_auth
    echo "pr-review: GitHub authentication OK." >&2
    exit 0
  fi

  if parse_url "$target"; then
    case "$PROVIDER" in
      github)
        FORCE_LOGIN=1
        github_ensure_auth
        echo "pr-review: GitHub authentication OK." >&2
        exit 0
        ;;
      gitlab)
        FORCE_LOGIN=1
        gitlab_ensure_auth
        echo "pr-review: GitLab authentication OK for $GITLAB_HOST." >&2
        exit 0
        ;;
    esac
  fi

  GITLAB_HOST="$target"
  FORCE_LOGIN=1
  gitlab_ensure_auth
  echo "pr-review: GitLab authentication OK for $GITLAB_HOST." >&2
  exit 0
}

truncate_diff() {
  local diff="$1"
  if ((${#diff} > MAX_BYTES)); then
    printf '%s\n\n...[diff truncated at %s bytes]...\n' "${diff:0:MAX_BYTES}" "$MAX_BYTES"
  else
    printf '%s' "$diff"
  fi
}

parse_url() {
  local u="$1"
  if [[ "$u" =~ ^https?://github\.com/([^/]+)/([^/]+)/pull/([0-9]+)/?(\?.*)?$ ]]; then
    PROVIDER=github
    GH_REPO="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
    PR_NUM="${BASH_REMATCH[3]}"
    return 0
  fi
  if [[ "$u" =~ ^https?://([^/]+)/(.+)/-/merge_requests/([0-9]+)/?(\?.*)?$ ]]; then
    PROVIDER=gitlab
    GITLAB_HOST="${BASH_REMATCH[1]}"
    GITLAB_PROJECT="${BASH_REMATCH[2]}"
    MR_IID="${BASH_REMATCH[3]}"
    return 0
  fi
  return 1
}

load_review_instructions() {
  if [[ -n "${PR_REVIEW_PROMPT_FILE:-}" && -f "$PR_REVIEW_PROMPT_FILE" ]]; then
    cat "$PR_REVIEW_PROMPT_FILE"
    return
  fi
  local py
  py="$(find_python)"
  [[ -n "$py" ]] || die "python3 not found (required for review instructions)"
  (cd "$REPO_ROOT" && PYTHONPATH="$REPO_ROOT" "$py" -c \
    "from agent.prompts import pr_review_rubric; print(pr_review_rubric(), end='')")
}

fetch_github() {
  github_ensure_auth
  META_JSON="$(gh pr view "$PR_NUM" -R "$GH_REPO" \
    --json title,body,baseRefName,headRefName,author,url,additions,deletions,changedFiles)" \
    || die "gh pr view failed for $GH_REPO#$PR_NUM (auth or access?)"
  DIFF="$(gh pr diff "$PR_NUM" -R "$GH_REPO")" \
    || die "gh pr diff failed for $GH_REPO#$PR_NUM"
  PLATFORM=GitHub
  REF_LABEL="$GH_REPO pull #$PR_NUM"
  WEB_URL="$(gh pr view "$PR_NUM" -R "$GH_REPO" --json url -q .url 2>/dev/null || true)"
}

fetch_gitlab() {
  gitlab_ensure_auth

  META_JSON="$(glab mr view "$MR_IID" -R "$GITLAB_PROJECT" -F json 2>/dev/null)" \
    || META_JSON="$(glab mr view "$MR_IID" -R "$GITLAB_PROJECT" --output json 2>/dev/null)" \
    || die "glab mr view failed for $GITLAB_HOST/$GITLAB_PROJECT!$MR_IID"

  gitlab_fetch_diff
  PLATFORM=GitLab
  REF_LABEL="$GITLAB_HOST/$GITLAB_PROJECT merge request !$MR_IID"
  if command -v jq >/dev/null 2>&1; then
    WEB_URL="$(printf '%s' "$META_JSON" | jq -r '.web_url // .webUrl // empty' 2>/dev/null || true)"
    TARGET_BRANCH="$(printf '%s' "$META_JSON" | jq -r '.target_branch // empty' 2>/dev/null || true)"
    SOURCE_BRANCH="$(printf '%s' "$META_JSON" | jq -r '.source_branch // empty' 2>/dev/null || true)"
    MR_TITLE="$(printf '%s' "$META_JSON" | jq -r '.title // empty' 2>/dev/null || true)"
  fi
}

run_llm() {
  local prompt_file="$1" py
  if [[ -n "${PR_REVIEW_LLM_CMD:-}" ]]; then
    <"$prompt_file" bash -c "$PR_REVIEW_LLM_CMD"
    return
  fi
  py="$(find_python)"
  if [[ -n "$py" ]]; then
    if (cd "$REPO_ROOT" && PYTHONPATH="$REPO_ROOT" "$py" -m agent.pr_review) <"$prompt_file"; then
      return
    fi
    die "Vertex review failed (check config/config.txt and gcloud auth application-default login)"
  fi
  if command -v cursor >/dev/null 2>&1; then
    cursor agent -p "$(cat "$prompt_file")"
    return
  fi
  if command -v claude >/dev/null 2>&1; then
    claude -p "$(cat "$prompt_file")"
    return
  fi
  die "no LLM configured. Use -p, set PR_REVIEW_LLM_CMD, or install python3 + anthropic[vertex] with config/config.txt"
}

if [[ "${1:-}" == "setup" ]]; then
  shift
  cmd_setup "${1:-all}"
  exit 0
fi

if [[ "${1:-}" == "auth" ]]; then
  shift
  cmd_auth "${1:-}"
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--out) OUT="$2"; shift 2 ;;
    -p|--prompt) PRINT_PROMPT=1; shift ;;
    --login) FORCE_LOGIN=1; shift ;;
    --install-deps) INSTALL_DEPS=1; shift ;;
    -h|--help) usage; exit 0 ;;
    -*) die "unknown option: $1 (try -h)" ;;
    *)
      if [[ -n "$URL" ]]; then
        die "unexpected argument: $1 (only one URL allowed)"
      fi
      URL="$1"
      shift
      ;;
  esac
done

[[ -n "$URL" ]] || { usage; die "missing URL"; }

parse_url "$URL" || die "unsupported URL (expected GitHub .../pull/N or GitLab .../-/merge_requests/N)"

ensure_provider_deps

PROVIDER="${PROVIDER:-}"
TARGET_BRANCH=""
SOURCE_BRANCH=""
MR_TITLE=""
WEB_URL=""
META_JSON=""
DIFF=""

case "$PROVIDER" in
  github) fetch_github ;;
  gitlab) fetch_gitlab ;;
  *) die "internal error: unknown provider" ;;
esac

if [[ "$PROVIDER" == github ]] && command -v jq >/dev/null 2>&1; then
  TARGET_BRANCH="$(printf '%s' "$META_JSON" | jq -r '.baseRefName // empty')"
  SOURCE_BRANCH="$(printf '%s' "$META_JSON" | jq -r '.headRefName // empty')"
  MR_TITLE="$(printf '%s' "$META_JSON" | jq -r '.title // empty')"
  WEB_URL="${WEB_URL:-$(printf '%s' "$META_JSON" | jq -r '.url // empty')}"
fi

DIFF_TRUNC="$(truncate_diff "$DIFF")"

CONTEXT_EXTRA=""
if [[ -n "${PR_REVIEW_CONTEXT_FILE:-}" && -f "$PR_REVIEW_CONTEXT_FILE" ]]; then
  CONTEXT_EXTRA="$(cat "$PR_REVIEW_CONTEXT_FILE")"
fi

PROMPT_FILE="$(mktemp)"
trap 'rm -f "$PROMPT_FILE"' EXIT

{
  load_review_instructions
  printf '\n\n---\n\n'
  printf '## Request\n\n'
  printf -- '- **Platform:** %s\n' "$PLATFORM"
  printf -- '- **Reference:** %s\n' "$REF_LABEL"
  [[ -n "$WEB_URL" ]] && printf -- '- **URL:** %s\n' "$WEB_URL"
  [[ -n "$MR_TITLE" ]] && printf -- '- **Title:** %s\n' "$MR_TITLE"
  [[ -n "$TARGET_BRANCH" ]] && printf -- '- **Merge target branch:** %s\n' "$TARGET_BRANCH"
  [[ -n "$SOURCE_BRANCH" ]] && printf -- '- **Source branch:** %s\n' "$SOURCE_BRANCH"
  printf '\n### Metadata (JSON)\n\n```json\n%s\n```\n\n' "$META_JSON"
  if [[ -n "$CONTEXT_EXTRA" ]]; then
    printf '### Additional context\n\n%s\n\n' "$CONTEXT_EXTRA"
  fi
  printf '### Diff\n\n```diff\n%s\n```\n' "$DIFF_TRUNC"
} >"$PROMPT_FILE"

if [[ "$PRINT_PROMPT" == 1 ]]; then
  cat "$PROMPT_FILE"
  exit 0
fi

if [[ -n "$OUT" ]]; then
  run_llm "$PROMPT_FILE" | tee "$OUT"
else
  run_llm "$PROMPT_FILE"
fi
