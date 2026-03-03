#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m';  GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m';     RESET='\033[0m'

ok()    { echo -e "${GREEN}[OK]${RESET}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${RESET} $*"; }
err()   { echo -e "${RED}[ERROR]${RESET} $*" >&2; }
info()  { echo -e "${CYAN}[INFO]${RESET} $*"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.venv"
VENV_ACTIVATE="${VENV_DIR}/bin/activate"
PYTHON_BIN="${VENV_DIR}/bin/python"
PIP_BIN="${VENV_DIR}/bin/pip"

BOT_ENTRY="${SCRIPT_DIR}/Main/Bot.py"
ENV_FILE="${SCRIPT_DIR}/Main/.env"
LOG_DIR="${SCRIPT_DIR}/Storage/Logs"
TEMP_DIR="${SCRIPT_DIR}/Storage/Temp"
PID_FILE="${TEMP_DIR}/bot.pid"
LOG_FILE="${LOG_DIR}/bot.log"
ROTATE_PREFIX="${LOG_DIR}/bot_"
MAX_LOG_BYTES=$((10 * 1024 * 1024))
MAX_ROTATED=5

_usage() {
    echo "Usage: ./bot.sh <command>"
    echo "Commands: start | stop | restart | status | logs | update"
}

_ensure_runtime_dirs() {
    mkdir -p "${LOG_DIR}" "${TEMP_DIR}"
}

_is_pid_running() {
    local pid="${1:-}"
    [[ "${pid}" =~ ^[0-9]+$ ]] || return 1
    kill -0 "${pid}" 2>/dev/null
}

_read_pid() {
    [[ -f "${PID_FILE}" ]] || return 1
    local pid
    pid="$(<"${PID_FILE}")"
    [[ "${pid}" =~ ^[0-9]+$ ]] || return 1
    printf "%s" "${pid}"
}

_cleanup_stale_pid() {
    if [[ -f "${PID_FILE}" ]]; then
        local pid
        pid="$(<"${PID_FILE}" || true)"
        if ! _is_pid_running "${pid}"; then
            rm -f "${PID_FILE}"
        fi
    fi
}

_check_venv() {
    if [[ ! -d "${VENV_DIR}" || ! -x "${PYTHON_BIN}" ]]; then
        err "Virtual environment not found. Run ./install.sh first."
        exit 1
    fi
}

_check_token() {
    if [[ ! -f "${ENV_FILE}" ]]; then
        err "DISCORD_TOKEN is not set in Main/.env. Run ./install.sh to configure it."
        exit 1
    fi

    local token=""
    local line
    while IFS= read -r line; do
        case "${line}" in
            DISCORD_TOKEN=*)
                token="${line#DISCORD_TOKEN=}"
                break
                ;;
        esac
    done < "${ENV_FILE}"
    token="${token#"${token%%[![:space:]]*}"}"
    token="${token%"${token##*[![:space:]]}"}"
    if [[ -z "${token}" ]]; then
        err "DISCORD_TOKEN is not set in Main/.env. Run ./install.sh to configure it."
        exit 1
    fi
}

_check_syntax() {
    local output
    if ! output="$("${PYTHON_BIN}" -m py_compile "${BOT_ENTRY}" 2>&1)"; then
        err "Main/Bot.py has a syntax error. Fix it before starting."
        echo "${output}" >&2
        exit 1
    fi
}

_check_prereqs() {
    _check_venv
    _check_token
    _check_syntax
}

_log_size_bytes() {
    if [[ ! -f "${LOG_FILE}" ]]; then
        echo 0
        return
    fi
    local size
    size="$(stat -c%s "${LOG_FILE}" 2>/dev/null || true)"
    if [[ -z "${size}" ]]; then
        size="$(stat -f%z "${LOG_FILE}" 2>/dev/null || echo 0)"
    fi
    echo "${size}"
}

_trim_rotated_logs() {
    local files=("${ROTATE_PREFIX}"*.log)
    [[ -e "${files[0]}" ]] || return 0

    while (( ${#files[@]} > MAX_ROTATED )); do
        local oldest_file="" oldest_mtime="" f mtime
        for f in "${files[@]}"; do
            mtime="$(stat -c%Y "${f}" 2>/dev/null || stat -f%m "${f}" 2>/dev/null || echo 0)"
            if [[ -z "${oldest_file}" || "${mtime}" -lt "${oldest_mtime}" ]]; then
                oldest_file="${f}"
                oldest_mtime="${mtime}"
            fi
        done
        [[ -n "${oldest_file}" ]] || break
        rm -f "${oldest_file}"
        files=("${ROTATE_PREFIX}"*.log)
        [[ -e "${files[0]}" ]] || break
    done
}

_rotate_log_if_needed() {
    local size
    size="$(_log_size_bytes)"
    if (( size <= MAX_LOG_BYTES )); then
        return
    fi

    local ts rotated
    ts="$(date +%Y%m%d_%H%M%S)"
    rotated="${ROTATE_PREFIX}${ts}.log"
    mv "${LOG_FILE}" "${rotated}"
    : > "${LOG_FILE}"
    _trim_rotated_logs
    info "Log rotated to ${rotated}"
}

_bot_uptime_pretty() {
    local pid="${1}"
    local etimes
    etimes="$(ps -o etimes= -p "${pid}" 2>/dev/null | tr -d '[:space:]')"
    [[ "${etimes}" =~ ^[0-9]+$ ]] || { echo "unknown"; return; }
    local h=$((etimes / 3600))
    local m=$(((etimes % 3600) / 60))
    local s=$((etimes % 60))
    echo "${h}h ${m}m ${s}s"
}

_start_bot() {
    _ensure_runtime_dirs
    _cleanup_stale_pid
    _check_prereqs

    if [[ -f "${PID_FILE}" ]]; then
        local existing_pid
        existing_pid="$(_read_pid || true)"
        if _is_pid_running "${existing_pid}"; then
            warn "Bot is already running (PID ${existing_pid}). Use ./bot.sh restart to reload it."
            return 0
        fi
        rm -f "${PID_FILE}"
    fi

    _rotate_log_if_needed

    bash -c "source \"${VENV_ACTIVATE}\" && exec python \"${BOT_ENTRY}\"" >> "${LOG_FILE}" 2>&1 &
    local pid=$!
    echo "${pid}" > "${PID_FILE}"

    ok "Coffeecord started (PID ${pid})"
    ok "Logging to Storage/Logs/bot.log"
}

_stop_bot() {
    _ensure_runtime_dirs
    _cleanup_stale_pid

    if [[ ! -f "${PID_FILE}" ]]; then
        info "Bot is not running."
        return 0
    fi

    local pid
    pid="$(_read_pid || true)"
    if ! _is_pid_running "${pid}"; then
        rm -f "${PID_FILE}"
        info "Bot is not running."
        return 0
    fi

    kill "${pid}" 2>/dev/null || true
    local waited=0
    while _is_pid_running "${pid}" && (( waited < 20 )); do
        sleep 0.5
        waited=$((waited + 1))
    done

    if _is_pid_running "${pid}"; then
        warn "Bot did not stop in time; sending SIGKILL."
        kill -9 "${pid}" 2>/dev/null || true
    fi

    rm -f "${PID_FILE}"
    ok "Coffeecord stopped."
}

_status_bot() {
    _ensure_runtime_dirs
    _cleanup_stale_pid

    if [[ -f "${PID_FILE}" ]]; then
        local pid
        pid="$(_read_pid || true)"
        if _is_pid_running "${pid}"; then
            local uptime last_line
            uptime="$(_bot_uptime_pretty "${pid}")"
            if [[ -f "${LOG_FILE}" ]]; then
                last_line="$(tail -n 1 "${LOG_FILE}" 2>/dev/null || true)"
            else
                last_line=""
            fi
            echo -e "${GREEN}●${RESET} Coffeecord — running"
            echo "  PID     : ${pid}"
            echo "  Uptime  : ${uptime}"
            echo "  Log     : Storage/Logs/bot.log  (last line: ${last_line:-<empty>})"
            return 0
        fi
    fi

    echo -e "○ Coffeecord — stopped"
}

_logs_bot() {
    _ensure_runtime_dirs
    if [[ ! -f "${LOG_FILE}" ]]; then
        info "No log file yet. Start the bot with ./bot.sh start"
        return 0
    fi

    if [[ "${1:-}" == "-n" ]]; then
        local n="${2:-}"
        if [[ ! "${n}" =~ ^[0-9]+$ ]]; then
            err "Usage: ./bot.sh logs -n <number>"
            exit 1
        fi
        tail -n "${n}" "${LOG_FILE}"
        return 0
    fi

    tail -f "${LOG_FILE}"
}

_update_bot() {
    _ensure_runtime_dirs
    _check_prereqs

    local was_running=false
    local current_pid
    current_pid="$(_read_pid || true)"
    if _is_pid_running "${current_pid}"; then
        was_running=true
        _stop_bot
    fi

    local pulled="skipped"
    if [[ -d "${SCRIPT_DIR}/.git" ]] && command -v git >/dev/null 2>&1; then
        info "Pulling latest changes..."
        git -C "${SCRIPT_DIR}" pull
        pulled="done"
    else
        warn "Not a git repository or git unavailable; skipping git pull."
    fi

    info "Updating dependencies..."
    "${PIP_BIN}" install -r "${SCRIPT_DIR}/requirements.txt" --quiet

    _check_syntax
    _start_bot

    echo ""
    ok "Update summary:"
    echo "  - Previously running: ${was_running}"
    echo "  - Git pull          : ${pulled}"
    echo "  - Dependencies      : updated"
    echo "  - Bot state         : running"
}

main() {
    local cmd="${1:-}"
    case "${cmd}" in
        start)
            _start_bot
            ;;
        stop)
            _stop_bot
            ;;
        restart)
            _stop_bot
            _start_bot
            ;;
        status)
            _status_bot
            ;;
        logs)
            shift || true
            _logs_bot "${1:-}" "${2:-}"
            ;;
        update)
            _update_bot
            ;;
        ""|-h|--help|help)
            _usage
            ;;
        *)
            _usage
            exit 1
            ;;
    esac
}

main "$@"
