# Opt-in Claude code-mode and all-project resume selection.
# Ordinary launches and explicit native UUID resumes keep native behavior.
_WORKBENCH_CLAUDE_HOME="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

_workbench_claude_python() {
    if [[ -n "${WORKBENCH_CLAUDE_PYTHON-}" && -x "$WORKBENCH_CLAUDE_PYTHON" ]]; then
        printf '%s\n' "$WORKBENCH_CLAUDE_PYTHON"
    elif [[ -x "$_WORKBENCH_CLAUDE_HOME/claude-sdk/bin/python" ]]; then
        printf '%s\n' "$_WORKBENCH_CLAUDE_HOME/claude-sdk/bin/python"
    else
        command -v python3
    fi
}

claude() {
    if [[ "${1-}" == --code ]]; then
        shift
        if [[ "${1-}" == --upgrade ]]; then
            shift
            python3 "$_WORKBENCH_CLAUDE_HOME/policy.py" --engine claude "$@"
        elif [[ "${1-}" == --resume ]]; then
            shift
            "$(_workbench_claude_python)" "$_WORKBENCH_CLAUDE_HOME/claude.py" dispatch -- --resume "$@"
        else
            python3 "$_WORKBENCH_CLAUDE_HOME/code-workflow.py" start --engine claude "$@"
        fi
    elif [[ "${1-}" == --resume || "${1-}" == -r ]]; then
        local candidate="${2-}"
        if [[ "$candidate" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]; then
            command claude "$@"
        else
            "$(_workbench_claude_python)" "$_WORKBENCH_CLAUDE_HOME/claude.py" dispatch -- "$@"
        fi
    else
        command claude "$@"
    fi
}
