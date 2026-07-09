#!/usr/bin/env bash
# =============================================================================
# setup_aws.sh — AWS CLI v2 Setup & Credential Configuration Guide
# Cloud Cost Optimizer project
# =============================================================================
set -euo pipefail

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

print_header() { echo -e "\n${BOLD}${BLUE}══════════════════════════════════════════${RESET}"; echo -e "${BOLD}${BLUE}  $1${RESET}"; echo -e "${BOLD}${BLUE}══════════════════════════════════════════${RESET}"; }
print_ok()     { echo -e "${GREEN}  ✔  $1${RESET}"; }
print_warn()   { echo -e "${YELLOW}  ⚠  $1${RESET}"; }
print_info()   { echo -e "${CYAN}  ℹ  $1${RESET}"; }
print_step()   { echo -e "\n${BOLD}  ▶  $1${RESET}"; }
print_cmd()    { echo -e "${YELLOW}     \$ $1${RESET}"; }
print_error()  { echo -e "${RED}  ✖  $1${RESET}"; }

# ── Detect OS ─────────────────────────────────────────────────────────────────
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ -f /etc/os-release ]]; then
        . /etc/os-release
        case "$ID" in
            ubuntu|debian) echo "debian" ;;
            amzn|rhel|centos|fedora) echo "rpm" ;;
            *) echo "linux" ;;
        esac
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)

# =============================================================================
echo ""
echo -e "${BOLD}${CYAN}  ☁  Cloud Cost Optimizer — AWS CLI Setup${RESET}"
echo -e "${CYAN}  ─────────────────────────────────────────${RESET}"

# =============================================================================
print_header "STEP 1 — Check for existing AWS CLI installation"

if command -v aws &>/dev/null; then
    CURRENT_VERSION=$(aws --version 2>&1 | head -1)
    print_ok "AWS CLI is already installed:"
    echo -e "     ${GREEN}${CURRENT_VERSION}${RESET}"

    # Confirm it's v2
    if echo "$CURRENT_VERSION" | grep -q "aws-cli/2"; then
        print_ok "Version confirmed: AWS CLI v2 ✔"
    else
        print_warn "You appear to have AWS CLI v1. v2 is recommended."
        print_info "See install instructions below to upgrade."
    fi
else
    print_warn "AWS CLI not found. Install instructions for your OS (${OS}):"

    echo ""
    case "$OS" in
        macos)
            echo -e "${BOLD}  macOS — Option A: Official PKG installer (recommended)${RESET}"
            print_cmd 'curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "/tmp/AWSCLIV2.pkg"'
            print_cmd 'sudo installer -pkg /tmp/AWSCLIV2.pkg -target /'
            echo ""
            echo -e "${BOLD}  macOS — Option B: Homebrew${RESET}"
            print_cmd 'brew install awscli'
            ;;
        debian)
            echo -e "${BOLD}  Ubuntu / Debian${RESET}"
            print_cmd 'curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "/tmp/awscliv2.zip"'
            print_cmd 'unzip /tmp/awscliv2.zip -d /tmp'
            print_cmd 'sudo /tmp/aws/install'
            ;;
        rpm)
            echo -e "${BOLD}  Amazon Linux / RHEL / CentOS / Fedora${RESET}"
            print_cmd 'curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "/tmp/awscliv2.zip"'
            print_cmd 'unzip /tmp/awscliv2.zip -d /tmp'
            print_cmd 'sudo /tmp/aws/install'
            ;;
        windows)
            echo -e "${BOLD}  Windows — Run in PowerShell as Administrator${RESET}"
            print_cmd 'msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi'
            echo ""
            print_info "Or download manually: https://awscli.amazonaws.com/AWSCLIV2.msi"
            ;;
        *)
            print_info "Could not detect OS. Visit: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
            ;;
    esac

    echo ""
    print_warn "After installing, re-run this script to continue setup."
    echo ""
    print_info "Cannot auto-install — user confirmation required for system-level installs."
    exit 0
fi

# =============================================================================
print_header "STEP 2 — Verify installation"

if aws --version &>/dev/null; then
    print_ok "$(aws --version 2>&1)"
else
    print_error "aws --version failed. Installation may be incomplete."
    exit 1
fi

# =============================================================================
print_header "STEP 3 — Where to find your AWS credentials"

cat << 'EOF'

  To run aws configure you need 4 pieces of information.
  Here is exactly where to find each one in the AWS Console:

  ┌─────────────────────────────────────────────────────────────┐
  │  ACCESS KEY ID & SECRET ACCESS KEY                          │
  │                                                             │
  │  1. Log in to https://console.aws.amazon.com                │
  │  2. Click your account name (top-right) → Security          │
  │     credentials                                             │
  │  3. Scroll to "Access keys" section                         │
  │  4. Click "Create access key"                               │
  │  5. Choose use case → "Command Line Interface (CLI)"        │
  │  6. Download the .csv or copy both values NOW               │
  │     ⚠ The Secret Access Key is shown ONCE — save it.       │
  │                                                             │
  │  If you are using an IAM user (not root):                   │
  │  IAM → Users → <your user> → Security credentials →        │
  │  Access keys → Create access key                            │
  └─────────────────────────────────────────────────────────────┘

EOF

# =============================================================================
print_header "STEP 4 — Run aws configure"

echo -e "  Run this command and enter each value when prompted:\n"
print_cmd "aws configure"

cat << 'EOF'

  You will be asked for 4 fields:

  ┌──────────────────────────────────────────────────────────────────┐
  │  Field                  │ What it means                         │
  ├──────────────────────────────────────────────────────────────────┤
  │  AWS Access Key ID      │ A 20-character alphanumeric ID that   │
  │                         │ identifies your AWS account/user.     │
  │                         │ Example: AKIAIOSFODNN7EXAMPLE         │
  │                         │                                       │
  │  AWS Secret Access Key  │ A 40-character secret key paired to  │
  │                         │ the Access Key ID. Treat it like a   │
  │                         │ password — never commit to git.       │
  │                         │ Example: wJalrXUtnFEMI/K7MDENG/...   │
  │                         │                                       │
  │  Default region name    │ The AWS region your resources live    │
  │                         │ in. For this project: us-east-1       │
  │                         │ (N. Virginia — lowest latency for     │
  │                         │ most AWS services)                    │
  │                         │                                       │
  │  Default output format  │ How the CLI formats its responses.    │
  │                         │ Use: json  (structured, easy to       │
  │                         │ parse with tools like jq)             │
  └──────────────────────────────────────────────────────────────────┘

  Example session:
  $ aws configure
  AWS Access Key ID [None]: AKIAIOSFODNN7EXAMPLE
  AWS Secret Access Key [None]: wJalrXUtnFEMI/K7MDENGbPxRfiCYEXAMPLEKEY
  Default region name [None]: us-east-1
  Default output format [None]: json

  Credentials are stored in: ~/.aws/credentials
  Config is stored in:       ~/.aws/config

EOF

# =============================================================================
print_header "STEP 5 — Verify credentials are working"

echo -e "  Run this command to confirm your credentials are valid:\n"
print_cmd "aws sts get-caller-identity"

echo ""
print_info "Attempting verification now..."
echo ""

if aws sts get-caller-identity 2>/dev/null; then
    echo ""
    print_ok "Credentials verified! Your AWS identity is shown above."
    print_ok "You are ready to use the Cloud Cost Optimizer with real AWS data."
else
    echo ""
    print_warn "Credentials not yet configured or invalid."
    echo ""
    echo -e "  ${BOLD}To configure, run:${RESET}"
    print_cmd "aws configure"
    echo ""
    echo -e "  ${BOLD}Then re-run the verification:${RESET}"
    print_cmd "aws sts get-caller-identity"
    echo ""
    print_info "If you see 'InvalidClientTokenId': your Access Key ID is wrong."
    print_info "If you see 'SignatureDoesNotMatch': your Secret Access Key is wrong."
    print_info "If you see 'ExpiredToken': your session token has expired (re-generate keys)."
fi

# =============================================================================
echo ""
echo -e "${BOLD}${GREEN}══════════════════════════════════════════${RESET}"
echo -e "${BOLD}${GREEN}  Setup complete.${RESET}"
echo -e "${BOLD}${GREEN}══════════════════════════════════════════${RESET}"
echo ""
echo -e "  ${BOLD}Next steps for Cloud Cost Optimizer:${RESET}"
echo -e "  1. Export your AWS Cost & Usage Report as CSV"
echo -e "  2. POST it to:  ${CYAN}http://localhost:8000/ingest${RESET}"
echo -e "  3. View results: ${CYAN}http://localhost:8000/dashboard${RESET}"
echo ""
