# Google Workspace Remote MCP Endpoints & Tools Reference

## Official Remote MCP Server URLs (Streamable HTTP)

| Service | Server Name | Remote MCP Endpoint | Common Tools |
| :--- | :--- | :--- | :--- |
| **Gmail** | `google-gmail` | `https://gmailmcp.googleapis.com/mcp/v1` | `search_threads`, `list_messages`, `get_message`, `get_thread`, `send_message`, `create_draft`, `list_labels` |
| **Google Drive** | `google-drive` | `https://drivemcp.googleapis.com/mcp/v1` | `search_files`, `get_file_metadata`, `read_file_content`, `create_folder`, `move_file`, `share_file` |
| **Google Calendar** | `google-calendar` | `https://calendarmcp.googleapis.com/mcp/v1` | `list_calendars`, `list_events`, `get_event`, `search_events`, `suggest_time`, `create_event`, `update_event`, `delete_event` |
| **Google Docs** | `google-docs` | `https://docsmcp.googleapis.com/mcp/v1` | `read_doc`, `create_doc`, `append_text`, `update_doc` |
| **Google Sheets** | `google-sheets` | `https://sheetsmcp.googleapis.com/mcp/v1` | `get_spreadsheet`, `read_range`, `create_spreadsheet`, `update_values`, `append_values` |
| **Google Slides** | `google-slides` | `https://slidesmcp.googleapis.com/mcp/v1` | `get_presentation`, `read_slide`, `create_presentation` |
| **Google Chat** | `google-chat` | `https://chatmcp.googleapis.com/mcp/v1` | `list_spaces`, `list_messages`, `get_message`, `create_message` |
| **Google Tasks** | `google-tasks` | `https://tasksmcp.googleapis.com/mcp/v1` | `list_tasklists`, `list_tasks`, `get_task`, `create_task`, `update_task` |

## Cross-Agent Tool Naming Convention

- **Hermes Agent / Claude Code / Codex / OpenCode:**
  `mcp__<sanitized_server_name>__<sanitized_tool_name>`
  Example: `google-drive` + `search_files` → `mcp__google_drive__search_files`
- **Antigravity / Cursor:**
  Tools appear under the configured server key (`google-drive` → `search_files`).

## Quota & Billing Tier Rules (Effective Nov 24, 2026 / Feb 1, 2027)

- **Standard Tier (Free):** Up to **5,000 requests/day per product per Google Cloud project**.
- **Scaled Tier (Paid):** Usage above daily free allowances is billed via Cloud Billing (starting April 1, 2027).
- **Access Boundary:** Grants access only to the signed-in Google account within the authorized scopes. Connect only the MCP servers required for your workflow.
