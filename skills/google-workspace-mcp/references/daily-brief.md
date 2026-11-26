# Daily / Morning Brief Procedure (MCP)

Follow this sequence when the user asks for a morning brief, daily schedule, or inbox triage:

1. **Resolve Time Context:** Determine the user's current local date and time zone (default `Asia/Bangkok` if not otherwise specified).
2. **Fetch Today's Calendar Events:**
   - Call `list_calendars` (if secondary calendars exist) and `list_events` covering `00:00:00` to `23:59:59` of the target date.
   - Flag overlapping events (schedule conflicts) and back-to-back meetings with zero buffer.
3. **Scan Priority Unread Emails:**
   - Call `search_threads` with query `is:unread newer_than:2d -category:promotions -category:social` (max 15 threads).
   - Call `get_thread` only on messages requiring action, approvals, deadlines, or meeting updates.
4. **Cross-Reference Meeting Prep:**
   - If a calendar event mentions a document title or agenda, optionally run `search_files` in Drive to surface the relevant doc link.
5. **Present Concise Summary:**
   - Group output into: **Schedule & Conflicts**, **Action-Required Emails**, and **Linked Docs** (omit empty sections).
