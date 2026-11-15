// The register as a read-only MCP server: JSON-RPC 2.0 over HTTP, no dependencies.
//
// All of the logic is here and takes the data as an argument, so node's test runner can drive
// it with a fixture (tests/mcp.test.mjs) and the Pages Function (functions/mcp.js) is only the
// HTTP layer. The data is api/schemes.json, which site/build.py writes from the same entries as
// schemes.csv: the server answers from this month's release and says which release that is.
//
// Read-only by construction: there is nothing here that writes, and nothing it could write to.

const PROTOCOL = "2025-06-18";
const MAX_PAGE = 50;

const INSTRUCTIONS =
  "The Schemes Register: Indian government schemes assembled monthly from official sources " +
  "(myScheme, DBT Bharat, the Union Budget and Outcome Budget, CAG audit reports and state budget " +
  "books), with what each source publishes about a scheme and what it leaves out. Read-only. " +
  "It describes the data about schemes, never whether a scheme works: a documentation gap such as " +
  "\"End date published here\" failing is a fact about the portal's record, not a judgement on the " +
  "scheme. Rows read from a state's budget book are heads that budget names: for a state with " +
  "no classifier they make no claim to be schemes, so treat them as budget lines. Use list_values for the exact state, ministry, sector or beneficiary spellings, " +
  "find_schemes to search, get_scheme for one scheme by id, documentation_gaps for what the " +
  "myScheme records leave out. Every answer carries a release code (schemes-register-YYYY.MM): " +
  "cite it with the attribution, and the data under CC BY 4.0.";

const str = { type: "string" };
const TOOLS = [
  {
    name: "find_schemes",
    description:
      "Search the register. Every filter is optional and they combine. state matches a state or UT " +
      "exactly (ignoring case); ministry, sector and beneficiary match part of the text; query needs " +
      "every word somewhere in the name, acronym, ministry or description. on_myscheme=false finds " +
      "schemes no citizen-facing national portal lists. Returns a page of schemes and the total.",
    inputSchema: {
      type: "object",
      properties: {
        query: str, state: str, ministry: str, sector: str, beneficiary: str,
        level: { type: "string", enum: ["central", "state"] },
        on_myscheme: { type: "boolean" },
        limit: { type: "integer", minimum: 1, maximum: MAX_PAGE, default: 20 },
        offset: { type: "integer", minimum: 0, default: 0 },
      },
    },
  },
  {
    name: "get_scheme",
    description:
      "One scheme by its id (the slug in its page URL, e.g. pm-kisan): where it applies, who runs it, " +
      "who it is for, its 2026-27 allocation where a budget names one, which sources list it, and " +
      "which documentation checks its myScheme record fails.",
    inputSchema: { type: "object", properties: { id: str }, required: ["id"] },
  },
  {
    name: "documentation_gaps",
    description:
      "What the myScheme records leave out. With no check: every documentation check with how many " +
      "records fail it. With a check id: the schemes whose record fails it, optionally in one state.",
    inputSchema: {
      type: "object",
      properties: {
        check: str, state: str,
        limit: { type: "integer", minimum: 1, maximum: MAX_PAGE, default: 20 },
        offset: { type: "integer", minimum: 0, default: 0 },
      },
    },
  },
  {
    name: "list_values",
    description:
      "The values a filter accepts, with how many schemes have each: state, ministry, sector, " +
      "beneficiary or source. Use it before find_schemes to get a spelling right.",
    inputSchema: {
      type: "object",
      properties: { field: { type: "string", enum: ["state", "ministry", "sector", "beneficiary", "source"] } },
      required: ["field"],
    },
  },
];

class ToolError extends Error {}

// Rows arrive as arrays to keep the file small; objects are made once per data set.
const cache = new WeakMap();
function schemes(data) {
  let s = cache.get(data);
  if (!s) {
    s = data.rows.map((r) => Object.fromEntries(data.fields.map((f, i) => [f, r[i]])));
    for (const x of s) x._text = [x.name, x.id, x.ministry, x.brief].join(" ").toLowerCase();
    cache.set(data, s);
  }
  return s;
}

const lc = (v) => String(v ?? "").toLowerCase();
const words = (q) => lc(q).split(/[^\p{L}\p{N}]+/u).filter(Boolean);

function opt(args, key, type) {
  const v = args[key];
  if (v === undefined || v === null || v === "") return undefined;
  if (typeof v !== type) throw new ToolError(`${key} must be a ${type}`);
  return v;
}

function page(args) {
  const limit = Math.min(Math.max(opt(args, "limit", "number") ?? 20, 1), MAX_PAGE);
  const offset = Math.max(opt(args, "offset", "number") ?? 0, 0);
  if (!Number.isInteger(limit) || !Number.isInteger(offset)) throw new ToolError("limit and offset must be integers");
  return { limit, offset };
}

const summary = (x) => ({
  id: x.id, name: x.name, level: x.level || null, states: x.states, ministry: x.ministry || null,
  sector: x.sector || null, budget_cr: x.budget_cr, on_myscheme: x.on_myscheme, url: x.url,
});

function findSchemes(data, args) {
  const q = words(opt(args, "query", "string"));
  const state = lc(opt(args, "state", "string"));
  const ministry = lc(opt(args, "ministry", "string"));
  const sector = lc(opt(args, "sector", "string"));
  const ben = lc(opt(args, "beneficiary", "string"));
  const level = opt(args, "level", "string");
  const onMs = opt(args, "on_myscheme", "boolean");
  const { limit, offset } = page(args);
  const hits = schemes(data).filter((x) =>
    (!state || x.states.some((s) => lc(s) === state)) &&
    (!ministry || lc(x.ministry).includes(ministry)) &&
    (!sector || lc(x.sector).includes(sector)) &&
    (!ben || lc([x.audience, ...x.beneficiaries].join(" ")).includes(ben)) &&
    (!level || (level === "central") === (lc(x.level) === "central")) &&
    (onMs === undefined || x.on_myscheme === onMs) &&
    q.every((w) => x._text.includes(w)));
  // A name that holds every word ranks above a description that does; otherwise by name.
  const inName = (x) => (q.length && q.every((w) => lc(x.name).includes(w)) ? 0 : 1);
  hits.sort((a, b) => inName(a) - inName(b) || a.name.localeCompare(b.name));
  return { total: hits.length, limit, offset, schemes: hits.slice(offset, offset + limit).map(summary) };
}

function getScheme(data, args) {
  const id = opt(args, "id", "string");
  if (!id) throw new ToolError("id is required");
  const x = schemes(data).find((s) => s.id === id.trim().toLowerCase());
  if (!x) throw new ToolError(`No scheme with id "${id}". Find ids with find_schemes.`);
  const { _text, ...scheme } = x;
  scheme.gaps = x.gaps.map((g) => data.meta.check_labels[g] || g);
  return { scheme };
}

function documentationGaps(data, args) {
  const check = opt(args, "check", "string");
  const labels = data.meta.check_labels;
  if (!check) {
    return {
      myscheme_records: data.meta.myscheme_records,
      note: "Only schemes with a myScheme record are checked; a scheme no national portal lists has no record to check.",
      checks: Object.entries(data.meta.by_check).map(([id, c]) => ({ check: id, label: labels[id] || id, ...c })),
    };
  }
  if (!(check in labels)) throw new ToolError(`Unknown check "${check}". Known: ${Object.keys(labels).join(", ")}`);
  const state = lc(opt(args, "state", "string"));
  const { limit, offset } = page(args);
  const hits = schemes(data).filter((x) => x.gaps.includes(check) && (!state || x.states.some((s) => lc(s) === state)));
  return { check, label: labels[check], total: hits.length, limit, offset, schemes: hits.slice(offset, offset + limit).map(summary) };
}

const VALUES = {
  state: (x) => x.states, ministry: (x) => [x.ministry], sector: (x) => [x.sector],
  beneficiary: (x) => x.beneficiaries, source: (x) => x.sources,
};

function listValues(data, args) {
  const field = opt(args, "field", "string");
  if (!VALUES[field]) throw new ToolError(`field must be one of ${Object.keys(VALUES).join(", ")}`);
  const n = new Map();
  for (const x of schemes(data)) for (const v of VALUES[field](x)) if (v) n.set(v, (n.get(v) || 0) + 1);
  return { field, values: [...n].sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(b[0])).slice(0, 300) };
}

const RUN = { find_schemes: findSchemes, get_scheme: getScheme, documentation_gaps: documentationGaps, list_values: listValues };

function callTool(params, data) {
  const run = RUN[params?.name];
  if (!run) throw new ToolError(`Unknown tool "${params?.name}"`);
  const out = {
    ...run(data, params.arguments || {}),
    release: data.meta.release, snapshot: data.meta.snapshot,
    licence: data.meta.licence, attribution: data.meta.attribution,
  };
  return { content: [{ type: "text", text: JSON.stringify(out) }], structuredContent: out };
}

/** One JSON-RPC request in, one response out, or null for a notification. */
export function handleMcp(req, data) {
  const id = req?.id ?? null;
  const ok = (result) => ({ jsonrpc: "2.0", id, result });
  if (!req || req.jsonrpc !== "2.0" || typeof req.method !== "string")
    return { jsonrpc: "2.0", id, error: { code: -32600, message: "Invalid request" } };
  if (req.id === undefined) return null;   // notifications/initialized and the like
  switch (req.method) {
    case "initialize":
      return ok({
        protocolVersion: PROTOCOL,
        capabilities: { tools: {} },
        serverInfo: { name: "schemes", version: data.meta.release },
        instructions: INSTRUCTIONS,
      });
    case "ping":
      return ok({});
    case "tools/list":
      return ok({ tools: TOOLS });
    case "tools/call":
      try {
        return ok(callTool(req.params, data));
      } catch (e) {
        if (!(e instanceof ToolError)) throw e;
        return ok({ isError: true, content: [{ type: "text", text: e.message }] });
      }
    default:
      return { jsonrpc: "2.0", id, error: { code: -32601, message: `Method not found: ${req.method}` } };
  }
}

export { TOOLS };
