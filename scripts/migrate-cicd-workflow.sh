#!/usr/bin/env bash
#
# migrate-cicd-workflow.sh - Migrate CI/CD workflow to another repository
#
# Usage:
#   ./migrate-cicd-workflow.sh [OPTIONS] <target-repo-path>
#
# Options:
#   --dry-run           Show what would be done without making changes
#   --bot-name NAME     Bot username for auto-approval (default: yourorg-bot)
#   --maintainer NAME   GitHub username to notify on ready-to-merge (default: repo owner)
#   --with-bot-setup    Prompt to configure bot account and PAT
#   --skip-labels       Skip creating GitHub labels
#   --help              Show this help message
#
# Examples:
#   ./migrate-cicd-workflow.sh ~/Projects/my-app
#   ./migrate-cicd-workflow.sh --bot-name mybot --maintainer alice ~/Projects/my-app
#   ./migrate-cicd-workflow.sh --dry-run ~/Projects/my-app
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script location (to find source files)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLC_ROOT="$(dirname "$SCRIPT_DIR")"

# Default values
DRY_RUN=false
BOT_NAME="yourorg-bot"
MAINTAINER=""
WITH_BOT_SETUP=false
SKIP_LABELS=false
TARGET_REPO=""

# Logging functions
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

show_help() {
    sed -n '3,18p' "$0" | sed 's/^# //' | sed 's/^#//'
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --bot-name)
            BOT_NAME="$2"
            shift 2
            ;;
        --maintainer)
            MAINTAINER="$2"
            shift 2
            ;;
        --with-bot-setup)
            WITH_BOT_SETUP=true
            shift
            ;;
        --skip-labels)
            SKIP_LABELS=true
            shift
            ;;
        --help|-h)
            show_help
            ;;
        -*)
            log_error "Unknown option: $1"
            exit 1
            ;;
        *)
            TARGET_REPO="$1"
            shift
            ;;
    esac
done

# Validate target repo
if [[ -z "$TARGET_REPO" ]]; then
    log_error "Target repository path is required"
    echo "Usage: $0 [OPTIONS] <target-repo-path>"
    exit 1
fi

# Resolve to absolute path
TARGET_REPO="$(cd "$TARGET_REPO" 2>/dev/null && pwd)" || {
    log_error "Target path does not exist: $TARGET_REPO"
    exit 1
}

# Verify it's a git repo
if [[ ! -d "$TARGET_REPO/.git" ]]; then
    log_error "Target is not a git repository: $TARGET_REPO"
    exit 1
fi

# Get repo info
cd "$TARGET_REPO"
REPO_REMOTE=$(git remote get-url origin 2>/dev/null || echo "")
if [[ -z "$REPO_REMOTE" ]]; then
    log_error "Could not determine remote origin"
    exit 1
fi

# Parse owner/repo from remote URL
if [[ "$REPO_REMOTE" =~ github\.com[:/]([^/]+)/([^/.]+) ]]; then
    REPO_OWNER="${BASH_REMATCH[1]}"
    REPO_NAME="${BASH_REMATCH[2]}"
else
    log_error "Could not parse GitHub owner/repo from: $REPO_REMOTE"
    exit 1
fi

# Default maintainer to repo owner
if [[ -z "$MAINTAINER" ]]; then
    MAINTAINER="$REPO_OWNER"
fi

log_info "Migration Configuration:"
echo "  Target:     $TARGET_REPO"
echo "  Repository: $REPO_OWNER/$REPO_NAME"
echo "  Bot:        $BOT_NAME"
echo "  Maintainer: $MAINTAINER"
echo "  Dry Run:    $DRY_RUN"
echo ""

# Source files
WORKFLOW_DIR="$CLC_ROOT/.github/workflows"
SCRIPTS_DIR="$CLC_ROOT/scripts"

# Target directories
TARGET_WORKFLOW_DIR="$TARGET_REPO/.github/workflows"
TARGET_SCRIPTS_DIR="$TARGET_REPO/scripts"

# Function to copy file with customization
copy_workflow() {
    local src="$1"
    local dst="$2"
    local filename=$(basename "$src")

    if $DRY_RUN; then
        log_info "[DRY RUN] Would copy $filename"
        return
    fi

    mkdir -p "$(dirname "$dst")"

    # Copy and customize
    sed -e "s/haighd-bot/$BOT_NAME/g" \
        -e "s/@haighd/@$MAINTAINER/g" \
        "$src" > "$dst"

    log_success "Copied $filename"
}

# Function to copy script
copy_script() {
    local src="$1"
    local dst="$2"
    local filename=$(basename "$src")

    if $DRY_RUN; then
        log_info "[DRY RUN] Would copy $filename"
        return
    fi

    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    chmod +x "$dst"
    log_success "Copied $filename (executable)"
}

# Function to create label
create_label() {
    local name="$1"
    local color="$2"
    local description="$3"

    if $DRY_RUN; then
        log_info "[DRY RUN] Would create label: $name"
        return
    fi

    if $SKIP_LABELS; then
        return
    fi

    # Check if label exists
    if gh label list --repo "$REPO_OWNER/$REPO_NAME" --json name -q ".[].name" | grep -q "^${name}$"; then
        log_info "Label already exists: $name"
    else
        gh label create "$name" \
            --repo "$REPO_OWNER/$REPO_NAME" \
            --color "$color" \
            --description "$description" 2>/dev/null || {
            log_warn "Could not create label: $name (may require permissions)"
        }
        log_success "Created label: $name"
    fi
}

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1: Copy Workflow Files"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

copy_workflow "$WORKFLOW_DIR/run-ci.yml" "$TARGET_WORKFLOW_DIR/run-ci.yml"
copy_workflow "$WORKFLOW_DIR/auto-approve.yml" "$TARGET_WORKFLOW_DIR/auto-approve.yml"
copy_workflow "$WORKFLOW_DIR/auto-resolve-outdated.yml" "$TARGET_WORKFLOW_DIR/auto-resolve-outdated.yml"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2: Copy Helper Scripts"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

copy_script "$SCRIPTS_DIR/categorize-findings.py" "$TARGET_SCRIPTS_DIR/categorize-findings.py"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3: Create GitHub Labels"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ! $SKIP_LABELS; then
    create_label "ready-to-merge" "0e8a16" "PR is approved and ready for final merge"
    create_label "do-not-merge" "d93f0b" "Blocks auto-approval - needs discussion"
else
    log_info "Skipping label creation (--skip-labels)"
fi

echo ""

# Bot setup
if $WITH_BOT_SETUP; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Step 4: Bot Account Setup"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    if $DRY_RUN; then
        log_info "[DRY RUN] Would prompt for bot PAT and add as collaborator"
    else
        echo ""
        echo "To enable auto-approval, you need a bot account with:"
        echo "  1. A Personal Access Token (PAT) with 'repo' scope"
        echo "  2. Write access to the repository"
        echo ""
        read -p "Enter bot PAT (or press Enter to skip): " BOT_PAT

        if [[ -n "$BOT_PAT" ]]; then
            # Add bot as collaborator
            log_info "Adding $BOT_NAME as collaborator..."
            gh api repos/"$REPO_OWNER/$REPO_NAME"/collaborators/"$BOT_NAME" \
                -X PUT \
                -f permission=push 2>/dev/null && log_success "Added $BOT_NAME as collaborator" || {
                log_warn "Could not add collaborator (may need owner permissions)"
            }

            # Set secret
            log_info "Setting BOT_PAT secret..."
            echo "$BOT_PAT" | gh secret set BOT_PAT \
                --repo "$REPO_OWNER/$REPO_NAME" 2>/dev/null && log_success "Set BOT_PAT secret" || {
                log_warn "Could not set secret (may need admin permissions)"
            }
        else
            log_info "Skipping bot setup"
        fi
    fi
    echo ""
fi

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Migration Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if $DRY_RUN; then
    echo -e "${YELLOW}This was a dry run. No changes were made.${NC}"
    echo "Run without --dry-run to apply changes."
else
    echo -e "${GREEN}Migration complete!${NC}"
fi

echo ""
echo "Files copied:"
echo "  .github/workflows/run-ci.yml"
echo "  .github/workflows/auto-approve.yml"
echo "  .github/workflows/auto-resolve-outdated.yml"
echo "  scripts/categorize-findings.py"
echo ""

# Manual steps
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Manual Steps Required"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. CUSTOMIZE BUILD STEPS (Required)"
echo "   Edit .github/workflows/run-ci.yml and update the 'python-checks' job"
echo "   with your project's actual build/test commands."
echo ""
echo "2. INSTALL GEMINI CODE ASSIST (Optional but recommended)"
echo "   Visit: https://github.com/marketplace/gemini-code-assist"
echo "   Click 'Install' and select your repository."
echo ""
echo "3. ENABLE GITHUB COPILOT (Optional)"
echo "   Settings → Copilot → Enable for this repository"
echo ""

if ! $WITH_BOT_SETUP; then
    echo "4. CONFIGURE BOT ACCOUNT (Optional, for auto-approval)"
    echo "   - Create a bot GitHub account (e.g., $BOT_NAME)"
    echo "   - Generate PAT with 'repo' scope"
    echo "   - Add bot as collaborator with Write access"
    echo "   - Set repository secret: BOT_PAT"
    echo "   Or re-run with --with-bot-setup flag"
    echo ""
fi

echo "5. COMMIT AND PUSH"
echo "   cd $TARGET_REPO"
echo "   git add .github/workflows scripts/categorize-findings.py"
echo "   git commit -m 'feat(ci): add dual AI reviewer workflow with severity gating'"
echo "   git push"
echo ""
echo "6. TEST WITH A SAMPLE PR"
echo "   Create a test PR and comment '/run-ci' to verify the workflow."
echo ""
