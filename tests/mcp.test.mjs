// The read-only MCP server's logic (site/mcp.mjs), run with `node --test tests/`.
// Node's own test runner: this repository installs nothing, and neither does this.
import { test } from "node:test";
import assert from "node:assert/strict";
import { handleMcp, TOOLS } from "../site/mcp.mjs";

const DATA = {
  meta: {
    release: "schemes-register-2026.11",
    snapshot: "2026-11-03",
    licence: "CC BY 4.0",
    attribution: "The Schemes Register (urbanmorph/schemes)",
    site: "https://india-schemes.pages.dev",
    myscheme_records: 3,
    check_labels: { end_date_recorded: "End date published here", benefit_quantified: "Benefit amount published here" },
    by_check: { end_date_recorded: { fail: 2, pass: 1, fail_pct: 66.7 }, benefit_quantified: { fail: 1, pass: 2, fail_pct: 33.3 } },
  },
  fields: ["id", "name", "level", "states", "sector", "ministry", "audience", "beneficiaries",
    "budget_cr", "sources", "on_myscheme", "checks_passed", "checks_total", "gaps", "brief", "url"],
  rows: [
    ["pm-kisan", "Pradhan Mantri Kisan Samman Nidhi", "Central", [], "Agriculture", "Ministry of Agriculture",
      "person", ["Farmer"], 63500, ["budget", "myscheme"], true, 8, 9, ["end_date_recorded"],
      "Income support of Rs 6,000 a year to farmer families.", "https://india-schemes.pages.dev/scheme/pm-kisan"],
    ["gruha-jyothi", "Gruha Jyothi", "State/ UT", ["Karnataka"], "Utility & Sanitation", "Energy Department",
      "person", ["Family"], null, ["myscheme"], true, 6, 9, ["end_date_recorded", "benefit_quantified"],
      "Free electricity up to 200 units for households.", "https://india-schemes.pages.dev/scheme/gruha-jyothi"],
    ["karnataka-anna-bhagya-123", "Anna Bhagya", "", ["Karnataka"], "", "Food Department",
      "", [], 8079.5, ["karnataka"], false, null, null, [], "", "https://india-schemes.pages.dev/scheme/karnataka-anna-bhagya-123"],
  ],
};

const call = (name, args = {}) => {
  const res = handleMcp({ jsonrpc: "2.0", id: 1, method: "tools/call", params: { name, arguments: args } }, DATA);
  assert.equal(res.result.isError, undefined, JSON.stringify(res.result));
  return res.result.structuredContent;
};

test("initialize names the server and says it is read-only", () => {
  const res = handleMcp({ jsonrpc: "2.0", id: 0, method: "initialize", params: {} }, DATA);
  assert.equal(res.result.serverInfo.name, "schemes");
  assert.match(res.result.instructions, /read-only/i);
  assert.ok(res.result.capabilities.tools);
});

test("notifications get no answer", () => {
  assert.equal(handleMcp({ jsonrpc: "2.0", method: "notifications/initialized" }, DATA), null);
});

test("tools/list lists the four tools, each with an input schema", () => {
  const res = handleMcp({ jsonrpc: "2.0", id: 2, method: "tools/list" }, DATA);
  assert.deepEqual(res.result.tools.map((t) => t.name).sort(),
    ["documentation_gaps", "find_schemes", "get_scheme", "list_values"]);
  for (const t of res.result.tools) assert.equal(t.inputSchema.type, "object");
  assert.equal(TOOLS.length, 4);
});

test("an unknown method is a JSON-RPC error", () => {
  const res = handleMcp({ jsonrpc: "2.0", id: 3, method: "resources/list" }, DATA);
  assert.equal(res.error.code, -32601);
});

test("find_schemes by state matches a state exactly, ignoring case", () => {
  const r = call("find_schemes", { state: "karnataka" });
  assert.deepEqual(r.schemes.map((s) => s.id).sort(), ["gruha-jyothi", "karnataka-anna-bhagya-123"]);
  assert.equal(r.total, 2);
});

test("find_schemes by text needs every word, and a name match ranks first", () => {
  const r = call("find_schemes", { query: "farmer income" });
  assert.deepEqual(r.schemes.map((s) => s.id), ["pm-kisan"]);
  const anna = call("find_schemes", { query: "anna" });
  assert.equal(anna.schemes[0].id, "karnataka-anna-bhagya-123");
});

test("find_schemes by ministry and beneficiary are substring matches", () => {
  assert.deepEqual(call("find_schemes", { ministry: "agriculture" }).schemes.map((s) => s.id), ["pm-kisan"]);
  assert.deepEqual(call("find_schemes", { beneficiary: "family" }).schemes.map((s) => s.id), ["gruha-jyothi"]);
});

test("find_schemes can ask for the schemes no citizen portal lists", () => {
  const r = call("find_schemes", { on_myscheme: false });
  assert.deepEqual(r.schemes.map((s) => s.id), ["karnataka-anna-bhagya-123"]);
});

test("find_schemes pages, and caps the page at 50", () => {
  const r = call("find_schemes", { limit: 1, offset: 1 });
  assert.equal(r.schemes.length, 1);
  assert.equal(r.total, 3);
  assert.equal(call("find_schemes", { limit: 500 }).limit, 50);
});

test("every answer carries the release code and the attribution", () => {
  const r = call("find_schemes", {});
  assert.equal(r.release, "schemes-register-2026.11");
  assert.match(r.attribution, /Schemes Register/);
  assert.equal(r.licence, "CC BY 4.0");
});

test("get_scheme returns one scheme with its gaps named in words", () => {
  const r = call("get_scheme", { id: "gruha-jyothi" });
  assert.equal(r.scheme.name, "Gruha Jyothi");
  assert.deepEqual(r.scheme.gaps, ["End date published here", "Benefit amount published here"]);
  assert.match(r.scheme.brief, /200 units/);
});

test("get_scheme on an unknown id is a tool error, not a crash", () => {
  const res = handleMcp({ jsonrpc: "2.0", id: 4, method: "tools/call",
    params: { name: "get_scheme", arguments: { id: "nope" } } }, DATA);
  assert.equal(res.result.isError, true);
  assert.match(res.result.content[0].text, /no scheme with id/i);
});

test("documentation_gaps with no check summarises every check", () => {
  const r = call("documentation_gaps");
  const end = r.checks.find((c) => c.check === "end_date_recorded");
  assert.equal(end.label, "End date published here");
  assert.equal(end.fail, 2);
  assert.equal(r.myscheme_records, 3);
});

test("documentation_gaps with a check lists the schemes that fail it, by state if asked", () => {
  const r = call("documentation_gaps", { check: "benefit_quantified" });
  assert.deepEqual(r.schemes.map((s) => s.id), ["gruha-jyothi"]);
  const none = call("documentation_gaps", { check: "end_date_recorded", state: "Kerala" });
  assert.equal(none.total, 0);
});

test("documentation_gaps refuses a check it does not know", () => {
  const res = handleMcp({ jsonrpc: "2.0", id: 5, method: "tools/call",
    params: { name: "documentation_gaps", arguments: { check: "made_up" } } }, DATA);
  assert.equal(res.result.isError, true);
});

test("list_values counts the values a filter accepts", () => {
  const r = call("list_values", { field: "state" });
  assert.deepEqual(r.values[0], ["Karnataka", 2]);
  assert.deepEqual(call("list_values", { field: "source" }).values.find((v) => v[0] === "myscheme"), ["myscheme", 2]);
});

test("a bad argument type is a tool error", () => {
  const res = handleMcp({ jsonrpc: "2.0", id: 6, method: "tools/call",
    params: { name: "find_schemes", arguments: { limit: "ten" } } }, DATA);
  assert.equal(res.result.isError, true);
});
