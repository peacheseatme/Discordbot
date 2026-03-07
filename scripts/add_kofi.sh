#!/usr/bin/env bash
# Add or update Ko-fi webhook configuration in Src/.env
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${CYAN}[INFO]${RESET}  $*"; }
success() { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
err()     { echo -e "${RED}[ERROR]${RESET} $*" >&2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/Src/.env"

if [[ ! -f "${ENV_FILE}" ]]; then
    err "Src/.env not found. Run ./install.sh first."
    exit 1
fi

# Check if Ko-fi is already configured (uncommented token)
if grep -qE '^KOFI_VERIFICATION_TOKEN=.+$' "${ENV_FILE}" 2>/dev/null; then
    warn "Ko-fi is already configured in Src/.env"
    read -rp "Overwrite? (y/N): " overwrite
    if [[ "${overwrite,,}" != "y" && "${overwrite,,}" != "yes" ]]; then
        info "Skipping. Run c-cord restart if the bot is not yet using Ko-fi."
        exit 0
    fi
fi

echo ""
echo -e "${BOLD}Ko-fi webhook setup${RESET}"
echo ""
echo "Get your verification token from: Ko-fi → Settings → Shop → Webhooks"
echo ""

read -rp "KOFI_VERIFICATION_TOKEN: " token
if [[ -z "${token}" ]]; then
    err "Token is required."
    exit 1
fi

read -rp "KOFI_PORT [5000]: " port
port="${port:-5000}"
if [[ ! "${port}" =~ ^[0-9]+$ ]]; then
    err "Port must be a number."
    exit 1
fi

# Replace or add KOFI vars; strip commented Ko-fi lines and add our block
tmp_file="${ENV_FILE}.tmp"
has_kofi=false

while IFS= read -r line || [[ -n "${line}" ]]; do
    if [[ "${line}" =~ ^KOFI_VERIFICATION_TOKEN= ]]; then
        echo "KOFI_VERIFICATION_TOKEN=${token}"
        has_kofi=true
        continue
    fi
    if [[ "${line}" =~ ^KOFI_PORT= ]]; then
        echo "KOFI_PORT=${port}"
        continue
    fi
    # Skip commented KOFI lines (we'll add uncommented below)
    if [[ "${line}" =~ ^#[[:space:]]*KOFI_VERIFICATION_TOKEN= ]]; then
        echo "KOFI_VERIFICATION_TOKEN=${token}"
        has_kofi=true
        continue
    fi
    if [[ "${line}" =~ ^#[[:space:]]*KOFI_PORT= ]]; then
        echo "KOFI_PORT=${port}"
        continue
    fi
    echo "${line}"
done < "${ENV_FILE}" > "${tmp_file}"

if [[ "${has_kofi}" != "true" ]]; then
    echo "" >> "${tmp_file}"
    echo "# ── Ko-fi integration ────────────────────────────────────────" >> "${tmp_file}"
    echo "KOFI_VERIFICATION_TOKEN=${token}" >> "${tmp_file}"
    echo "KOFI_PORT=${port}" >> "${tmp_file}"
fi

mv "${tmp_file}" "${ENV_FILE}"
success "Updated Src/.env with Ko-fi settings."

echo ""
echo -e "${BOLD}Next steps:${RESET}"
echo ""
echo "  1. Start the bot:  c-cord start  (or c-cord restart)"
echo "     ngrok will start automatically to expose port ${port}."
echo "  2. In Ko-fi → Settings → Shop → Webhooks, set URL to:"
echo "     https://<your-ngrok-url>/kofi-webhook"
echo "  3. Use the same verification token in Ko-fi's webhook settings."
echo "  4. Run 'ngrok config add-authtoken <token>' if you haven't yet."
echo ""
