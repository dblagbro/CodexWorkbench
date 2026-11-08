# Local extension: `codex --code [--one-off] ["initial task"]`.
# All ordinary Codex invocations retain their original behavior.
_CODEX_CODE_HOME="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
codex() {
    if [[ "${1-}" == --code ]]; then
        shift
        if [[ "${1-}" == --upgrade ]]; then
            shift
            python3 "$_CODEX_CODE_HOME/policy.py" "$@"
            return $?
        fi
        if [[ "${1-}" == --resume ]]; then
            shift
            codex --coderesume "$@"
            return $?
        fi
        python3 "$_CODEX_CODE_HOME/code-workflow.py" start "$@"
    elif [[ "${1-}" == --coderesume || "${1-}" == -cr ]]; then
        shift
        if [[ "${1-}" == --host ]]; then
            shift
            local resume_host="${1-}"
            if [[ -z "$resume_host" ]]; then
                echo 'Supply an SSH host after --host.' >&2
                return 2
            fi
            shift
            python3 "$_CODEX_CODE_HOME/resume.py" --host "$resume_host" resume "$@"
            return $?
        fi
        command codex resume --all "$@"
    else
        command codex "$@"
    fi
}

# Separate command names avoid collisions with present or future Codex flags.
cx() {
    python3 "$_CODEX_CODE_HOME/code-workflow.py" start "$@"
}

cxr() {
    codex --coderesume "$@"
}

# Claude integration is explicitly enabled by installer --with-claude.
if [[ -f "$_CODEX_CODE_HOME/claude-enabled" && -f "$_CODEX_CODE_HOME/claude-shell.bash" ]]; then
    source "$_CODEX_CODE_HOME/claude-shell.bash"
fi
