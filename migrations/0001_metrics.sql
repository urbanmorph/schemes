-- schemes' MCP use: first-party, server-side, aggregate (site/metrics.mjs). One counter per
-- day per dimension per key. No IP, no user agent, no client name as sent, no arguments, no
-- per-user rows. Dimensions are counted separately and never joined.
--
-- dim         key
-- mode        mcp                          (an initialize, bots and monitors aside)
-- mcp_client  monitor | claude-code | claude-ai | cursor | codex | chatgpt | windsurf |
--             vscode | gemini | cline | zed | inspector | other
-- mcp_tool    find_schemes | get_scheme | documentation_gaps | list_values

CREATE TABLE IF NOT EXISTS daily (
  day  TEXT NOT NULL,              -- UTC date, YYYY-MM-DD
  dim  TEXT NOT NULL,
  key  TEXT NOT NULL,
  n    INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (day, dim, key)
);
