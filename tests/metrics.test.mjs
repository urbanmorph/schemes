// MCP use counts (site/metrics.mjs), run with `node --test tests/`.
import { test } from "node:test";
import assert from "node:assert/strict";
import { mcpClient, MCP_CLIENTS, isBot, mcpCounts, record, count } from "../site/metrics.mjs";

// The one list shared by ops, yellide (overlooked), mugilu, irrational and schemes, agreed 23 Nov 2026.
// These cases are ops-dashboard/worker/test/mcp-clients.test.js's, word for word.
test("MCP client names land in the shared products", () => {
  const cases = [
    ["claude-code", "claude-code"], ["Claude Code", "claude-code"], ["claude.ai", "claude-ai"], ["Claude Desktop", "claude-ai"],
    ["Cursor-VSCode", "cursor"], ["codex-mcp-client", "codex"], ["openai-mcp", "chatgpt"], ["codeium", "windsurf"],
    ["Visual Studio Code", "vscode"], ["cline-vscode", "vscode"], ["cline", "cline"], ["gemini-cli", "gemini"],
    ["zed", "zed"], ["mcp-inspector", "inspector"],
    // uptime checks, probes and directories are monitors, whatever product word they carry
    ["mcpbeat", "monitor"], ["glimind-probe", "monitor"], ["mcptry-health-check", "monitor"], ["hostedmcp-liveness", "monitor"],
    ["posthog-mcp-registry-probe", "monitor"], ["glama", "monitor"], ["glama-mcp-inspector", "monitor"],
    ["ziwei-seat", "other"], ["", "other"], [null, "other"],
  ];
  for (const [name, want] of cases) assert.equal(mcpClient(name), want, String(name));
});

test("every product maps to itself, so grouping twice changes nothing", () => {
  assert.deepEqual(MCP_CLIENTS, ["monitor", "claude-code", "claude-ai", "cursor", "codex", "chatgpt", "windsurf", "vscode",
    "gemini", "cline", "zed", "inspector", "other"]);
  for (const p of MCP_CLIENTS) assert.equal(mcpClient(p), p);
});

const TOOLS = ["find_schemes", "get_scheme", "documentation_gaps", "list_values"];
const init = (name) => ({ jsonrpc: "2.0", id: 0, method: "initialize", params: { clientInfo: { name, version: "1" } } });
const call = (name) => ({ jsonrpc: "2.0", id: 1, method: "tools/call", params: { name, arguments: { id: "secret-query" } } });
const UA = "node";   // a script is use; isBot() says which agents are not

test("an initialize counts the mode and the client product, never the name as sent", () => {
  assert.deepEqual(mcpCounts(init("Claude Code"), UA, TOOLS), [["mode", "mcp"], ["mcp_client", "claude-code"]]);
  assert.deepEqual(mcpCounts(init("my-own-agent-for-acme"), UA, TOOLS), [["mode", "mcp"], ["mcp_client", "other"]]);
  assert.deepEqual(mcpCounts(init("mcp-inspector"), UA, TOOLS), [["mode", "mcp"], ["mcp_client", "inspector"]]);
});

test("a monitor counts as mcp_client = monitor but never as mode = mcp", () => {
  assert.deepEqual(mcpCounts(init("mcpbeat"), UA, TOOLS), [["mcp_client", "monitor"]]);
  // nor do the tool calls it sends in the same batch
  assert.deepEqual(mcpCounts([init("glama-mcp-inspector"), call("get_scheme")], UA, TOOLS), [["mcp_client", "monitor"]]);
});

test("a tool call counts its tool, never its arguments, and only a tool the server has", () => {
  assert.deepEqual(mcpCounts(call("get_scheme"), UA, TOOLS), [["mcp_tool", "get_scheme"]]);
  assert.deepEqual(mcpCounts(call("drop_tables"), UA, TOOLS), []);
  assert.deepEqual(mcpCounts(call({ toString: () => "x" }), UA, TOOLS), []);
});

test("bots, other methods and junk count nothing", () => {
  assert.equal(isBot("UptimeRobot/2.0"), true);
  assert.equal(isBot(""), true);
  assert.equal(isBot("node"), false);
  assert.deepEqual(mcpCounts(init("claude-code"), "Googlebot/2.1", TOOLS), []);
  assert.deepEqual(mcpCounts({ jsonrpc: "2.0", id: 2, method: "tools/list" }, UA, TOOLS), []);
  for (const junk of [null, 7, "x", [null, 3], { method: "initialize", params: null }])
    assert.doesNotThrow(() => mcpCounts(junk, UA, TOOLS));
  assert.deepEqual(mcpCounts({ method: "initialize", params: null }, UA, TOOLS), [["mode", "mcp"], ["mcp_client", "other"]]);
});

function fakeDb() {
  const rows = new Map();
  return {
    rows,
    prepare: (sql) => ({ bind: (day, dim, key) => ({ sql, day, dim, key }) }),
    batch: async (stmts) => { for (const s of stmts) rows.set(`${s.day}|${s.dim}|${s.key}`, (rows.get(`${s.day}|${s.dim}|${s.key}`) || 0) + 1); },
  };
}

test("record adds each counter for the day and never throws", async () => {
  const db = fakeDb();
  await record(db, "2026-11-23", [["mode", "mcp"], ["mcp_client", "cursor"]]);
  await record(db, "2026-11-23", [["mode", "mcp"]]);
  assert.deepEqual([...db.rows], [["2026-11-23|mode|mcp", 2], ["2026-11-23|mcp_client|cursor", 1]]);
  await record({ prepare: () => { throw new Error("D1 down"); } }, "2026-11-23", [["mode", "mcp"]]);
  await record({ prepare: () => ({ bind: () => ({}) }), batch: async () => { throw new Error("D1 down"); } }, "2026-11-23", [["mode", "mcp"]]);
  await record(undefined, "2026-11-23", [["mode", "mcp"]]);
});

const req = (ua = UA) => new Request("https://india-schemes.pages.dev/mcp", { method: "POST", headers: { "user-agent": ua } });

test("count hands the write to waitUntil and returns at once", async () => {
  const db = fakeDb(), later = [];
  assert.equal(count(req(), { DB: db }, (p) => later.push(p), init("cursor"), TOOLS, new Date("2026-11-23T10:00:00Z")), undefined);
  assert.equal(later.length, 1);
  await later[0];
  assert.deepEqual([...db.rows], [["2026-11-23|mode|mcp", 1], ["2026-11-23|mcp_client|cursor", 1]]);
});

test("count never throws: no binding, a broken waitUntil, a broken request", () => {
  const later = [];
  count(req(), {}, (p) => later.push(p), init("cursor"), TOOLS);
  count(req(), undefined, (p) => later.push(p), init("cursor"), TOOLS);
  assert.equal(later.length, 0);
  count(req(), { DB: fakeDb() }, () => { throw new Error("no waitUntil"); }, init("cursor"), TOOLS);
  count(null, { DB: fakeDb() }, (p) => later.push(p), init("cursor"), TOOLS);
  count(req(), { DB: fakeDb() }, undefined, init("cursor"), TOOLS);
});
