# google-workspace-mcp

Google Workspace (**Gmail, Drive, Calendar, Docs, Sheets, Slides, Chat, Tasks**) integration via **official Google-hosted Remote MCP Servers** — compliant with Google's Workspace AI Tools Addendum and the February 1, 2027 AI Agent MCP mandate.

Supports both **Free Standard Tier** (Personal Mode, up to 5,000 requests/day per product) and **Paid Scaled Tier** (higher quotas with Cloud Billing), and works across **Hermes Agent** (CLI, Desktop App, multi-profile, and Docker/SSH), **Claude Code**, **Cursor**, **OpenCode**, **Codex CLI**, and **Antigravity / Gemini CLI**.

---

## Repository Structure

```text
google-workspace-mcp/
├── README.md
├── .gitignore
├── skills.sh.json                        # Hermes Desktop App / Tap category metadata
├── .claude-plugin/
│   └── marketplace.json                  # Claude Code official plugin marketplace manifest
└── skills/
    └── google-workspace-mcp/
        ├── SKILL.md                      # Main agent skill instructions (agentskills.io standard)
        ├── scripts/
        │   └── setup_mcp.py              # Zero-dependency auto-detector, skill installer & config merger
        └── references/
            ├── mcp-endpoints-and-tools.md
            ├── gmail-search-syntax.md
            └── daily-brief.md
```

---

## Step 1: Create Google Cloud OAuth Credentials

Google requires OAuth clients used with Workspace MCP servers to have the **AI-powered agent** flag (`isAgent=true`) enabled:

1. Open Google Cloud Console > **Configure the Google Workspace MCP servers** > click **Set up personal mode** for single-account use (or configure an Internal / External OAuth client for multi-user teams).
2. Select or create a Google Cloud project and accept the **Google API Services User Data Policy** (this automatically enables Workspace APIs and `*mcp.googleapis.com` endpoints).
3. Choose OAuth Client type:
   - **Desktop app** for Hermes Agent (CLI / Desktop / Docker), Claude Code, Cursor, OpenCode, or Codex CLI.
   - **Web application** for web-based connectors (Antigravity / Claude Web) with their exact redirect URI.
4. Confirm **Use this client for an AI-powered agent** is checked, then copy your **Client ID** and **Client Secret**.
5. *(Optional — Paid Scaled Tier)*: Projects default to the free **Standard Tier** (5,000 requests/day per product). To raise quotas, link a Cloud Billing account and switch to **Scaled Tier** in the Workspace API Usage Dashboard — no changes to this skill are required.

---

## Step 2: Install & Configure by Agent

### Option A: Hermes Agent (CLI — Default or Named Profile)

```bash
# 1. Install skill into your target profile (omit `-p <profile>` for default ~/.hermes)
hermes -p <profile-name> skills install jhomhermes/google-workspace-mcp/google-workspace-mcp

# 2. Save OAuth credentials to the profile's .env
python3 ~/.hermes/profiles/<profile-name>/skills/productivity/google-workspace-mcp/scripts/setup_mcp.py \
  --profile <profile-name> --write-env \
  --client-id "YOUR_CLIENT_ID" --client-secret "YOUR_CLIENT_SECRET"

# 3. Automatically merge MCP servers into the profile's config.yaml (creates config.yaml.bak)
python3 ~/.hermes/profiles/<profile-name>/skills/productivity/google-workspace-mcp/scripts/setup_mcp.py \
  --profile <profile-name> --apply --services gmail,drive,calendar

# 4. Authenticate each enabled MCP server
hermes -p <profile-name> mcp login google-gmail --connect-timeout 300
hermes -p <profile-name> mcp login google-drive --connect-timeout 300
hermes -p <profile-name> mcp login google-calendar --connect-timeout 300
```

> **Custom `HERMES_HOME` / Container Profiles:** If `HERMES_HOME` is exported (for example `HERMES_HOME=/opt/data/profiles/2ai-programmer`), `setup_mcp.py` detects it automatically without needing `--profile`.

---

### Option B: Hermes Desktop App

1. Open **Hermes Desktop** > **Skills** > **Add GitHub Repo / Tap** and enter `jhomhermes/google-workspace-mcp`.
2. Install **`google-workspace-mcp`** into your desired profile.
3. Open a chat in that profile and invoke `/google-workspace-mcp` — the agent will guide you through saving credentials and running `setup_mcp.py --apply` to update `config.yaml`.

---

### Option C: Claude Code (Official Plugin Marketplace)

Inside Claude Code:

```text
/plugin marketplace add jhomhermes/google-workspace-mcp
/plugin install google-workspace-mcp@google-workspace-mcp
```

Then configure `~/.claude.json` automatically and authenticate:

```bash
export GOOGLE_MCP_CLIENT_ID="YOUR_CLIENT_ID"
export GOOGLE_MCP_CLIENT_SECRET="YOUR_CLIENT_SECRET"
python3 ~/.claude/skills/google-workspace-mcp/scripts/setup_mcp.py --client claude --apply --services gmail,drive,calendar
```

Inside Claude Code, run `/mcp`, select each `google-*` server, and click **Authenticate**.

---

### Option D: Clone & Auto-Detect Installer (All Supported Agents)

```bash
git clone https://github.com/jhomhermes/google-workspace-mcp.git
cd google-workspace-mcp

# Detect installed CLIs/agents and launch interactive installer
python3 skills/google-workspace-mcp/scripts/setup_mcp.py

# Or install non-interactively across all detected agents
python3 skills/google-workspace-mcp/scripts/setup_mcp.py --install --all-detected --services gmail,drive,calendar
```

---

## Headless Server / Docker Setup (SSH Port Forwarding)

When running on a remote Linux host or Docker container without a local browser, pass `--headless` to pin deterministic localhost callback ports (`8765`, `8766`, ...):

```bash
python3 skills/google-workspace-mcp/scripts/setup_mcp.py --install --client hermes --services gmail,drive,calendar --headless
```

Open an SSH tunnel from your local workstation before running `hermes mcp login`:

```bash
ssh -L 8765:127.0.0.1:8765 -L 8766:127.0.0.1:8766 -L 8767:127.0.0.1:8767 user@your-server-ip
```
