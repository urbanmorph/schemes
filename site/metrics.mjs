// How the MCP server is used: aggregate daily counters in D1, as yellide counts its own
// (overlooked/functions/lib/metrics.js and lib/mcp.js). Never who: no IP, no user agent, no
// client name as sent, no arguments, no per-user rows ("never who", 18 Nov 2026). Each counter
// is a separate (day, dim, key) row, so two facts about one request are never stored together.
// Counting is best-effort and never changes or slows a response: functions/mcp.js calls count()
// after building its answer, and the write runs in waitUntil. Without the DB binding nothing is
// counted. Tested by tests/metrics.test.mjs; the table is migrations/0001_metrics.sql.
//
// dim         key
// mode        mcp                          (an initialize, bots and monitors aside)
// mcp_client  one of MCP_CLIENTS           (the client product, from clientInfo.name)
// mcp_tool    find_schemes, get_scheme, …  (each tools/call of a tool this server has)

// MCP client products, from the client's own name at initialize; anything else is 'other', so a name someone gave
// their own client is never kept. The first match wins: a probe is a monitor whatever product it names, and
// cursor-vscode is cursor. One list for ops, yellide (overlooked), mugilu, irrational and schemes, agreed 23 Nov 2026:
// the reference copy is ops-dashboard/worker/src/mcp-clients.js; keep the copies identical. A product name maps to itself.
const CLIENTS = [
  ['monitor', /probe|health|check|liveness|monitor|uptime|beat|registry|directory|census|catalog|glama/],
  ['claude-code', /claude[ -]?code/], ['claude-ai', /claude/], ['cursor', /cursor/], ['codex', /codex/],
  ['chatgpt', /chatgpt|openai/], ['windsurf', /windsurf|codeium/], ['vscode', /visual studio code|vscode|copilot/],
  ['gemini', /gemini/], ['cline', /\bcline\b/], ['zed', /^zed\b/], ['inspector', /inspector/],
];
export const MCP_CLIENTS = [...CLIENTS.map(([k]) => k), 'other'];

/** The MCP client product for a clientInfo.name: one of MCP_CLIENTS. */
export function mcpClient(name) {
  const s = typeof name === 'string' ? name.toLowerCase().slice(0, 100) : '';
  return CLIENTS.find(([, re]) => re.test(s))?.[0] ?? 'other';
}

/** Crawlers, monitors, link previews and empty agents: not use. Scripts (curl, python, node) and AI clients acting for
 *  a person are use. yellide's isBot(), word for word. */
export function isBot(ua) {
  return !ua || /bot|crawl|spider|slurp|headless|lightpanda|scan|monitor|uptime|preview|facebookexternalhit|whatsapp|telegram|embedly|bytespider|google-extended|meta-external|cohere-ai/i.test(ua);
}

/** The [dim, key] counters one POST body (a message or a batch) adds. `tools` are the server's tool names. Pure. */
export function mcpCounts(body, ua, tools) {
  if (isBot(ua)) return [];
  const out = [];
  let monitor = false;
  for (const m of Array.isArray(body) ? body : [body]) {
    if (!m || typeof m !== 'object') continue;
    if (m.method === 'initialize') {
      const product = mcpClient(m.params?.clientInfo?.name);
      monitor ||= product === 'monitor';
      out.push(['mode', 'mcp'], ['mcp_client', product]);
    } else if (m.method === 'tools/call' && tools.includes(m.params?.name)) {
      out.push(['mcp_tool', m.params.name]);
    }
  }
  // a monitor (an uptime check, a registry probe) is counted as one, and nothing it does is use
  return monitor ? out.filter(([dim]) => dim === 'mcp_client') : out;
}

const UPSERT = 'INSERT INTO daily (day, dim, key, n) VALUES (?, ?, ?, 1) ON CONFLICT(day, dim, key) DO UPDATE SET n = n + 1';

/** Add the counters to D1 in one batch. Does nothing without a binding; never throws. */
export async function record(db, day, pairs) {
  if (!db || !pairs.length) return;
  try {
    const upsert = db.prepare(UPSERT);
    await db.batch(pairs.map(([dim, key]) => upsert.bind(day, dim, key)));
  } catch {
    // best-effort: metrics must never surface to a client
  }
}

/** Count one MCP request after its answer is built: the write goes to waitUntil, so this returns at once. Never throws. */
export function count(request, env, waitUntil, body, tools, now = new Date()) {
  if (!env?.DB) return;
  try {
    const pairs = mcpCounts(body, request.headers.get('user-agent'), tools);
    if (pairs.length) waitUntil(record(env.DB, now.toISOString().slice(0, 10), pairs));
  } catch {
    // metrics must never change a response
  }
}
