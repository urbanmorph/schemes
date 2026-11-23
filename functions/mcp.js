// Cloudflare Pages Function: the register's read-only MCP server at /mcp (streamable HTTP,
// stateless JSON-RPC). All the logic is site/mcp.mjs, tested by tests/mcp.test.mjs; this is
// the HTTP layer and the data load. It is the only code on this site that runs on a request;
// every other path is a static file (Pages routes only /mcp here).
//
// The data is the site's own api/schemes.json, read through the static-asset binding once per
// isolate and kept: it changes only when the site is redeployed, which starts new isolates.
//
// Each request is counted after its answer is built (site/metrics.mjs): the D1 write runs in
// waitUntil, and without the DB binding nothing is counted, so counting never changes or slows
// an answer.
import { handleMcp, TOOLS } from "../site/mcp.mjs";
import { count } from "../site/metrics.mjs";

const TOOL_NAMES = TOOLS.map((t) => t.name);

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Accept, Mcp-Session-Id, Mcp-Protocol-Version",
};

const json = (body, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json", ...CORS } });

let data = null;
async function load(env, request) {
  if (!data) {
    const r = await env.ASSETS.fetch(new URL("/api/schemes.json", request.url));
    if (!r.ok) throw new Error(`api/schemes.json answered ${r.status}`);
    data = await r.json();
  }
  return data;
}

export const onRequestOptions = () => new Response(null, { status: 204, headers: CORS });

export const onRequestGet = () =>
  json({
    name: "schemes",
    transport: "streamable-http (POST JSON-RPC 2.0: initialize, tools/list, tools/call)",
    tools: ["find_schemes", "get_scheme", "documentation_gaps", "list_values"],
    docs: "https://india-schemes.pages.dev/llms.txt",
  });

export async function onRequestPost({ request, env, waitUntil }) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "Parse error" } }, 400);
  }
  const d = await load(env, request);
  const out = Array.isArray(body) ? body.map((r) => handleMcp(r, d)).filter(Boolean) : handleMcp(body, d);
  const res = out === null ? new Response(null, { status: 202, headers: CORS }) : json(out);
  count(request, env, waitUntil, body, TOOL_NAMES);
  return res;
}
