# Gmail Search Operators Reference

Use these operators inside Gmail MCP search tools (`search_threads` / `list_messages`):

| Operator | Example | Meaning |
| :--- | :--- | :--- |
| `is:unread` | `is:unread` | Unread messages only |
| `is:starred` | `is:starred` | Starred messages |
| `from:` | `from:alerts@google.com` | Sender address or name |
| `to:` | `to:me` | Recipient address |
| `subject:` | `subject:"invoice"` | Words in subject line |
| `newer_than:` | `newer_than:2d` | Relative age (`d` = days, `m` = months, `y` = years) |
| `older_than:` | `older_than:7d` | Older than relative duration |
| `after:` / `before:` | `after:2026/11/01` | Specific date (`YYYY/MM/DD`) |
| `has:attachment` | `has:attachment filename:pdf` | Messages with specific attachments |
| `label:` | `label:important` | Messages with specific label |
| `-` (exclude) | `is:unread -category:promotions` | Exclude matching messages |
