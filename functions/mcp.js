// Cloudflare Pages Function: the register's read-only MCP server at /mcp (streamable HTTP,
// stateless JSON-RPC). All the logic is site/mcp.mjs, tested by tests/mcp.test.mjs; this is
// the HTTP layer and the data load. It is the only code on this site that runs on a request;
// every other path is a static file (Pages routes only /mcp here).
//
// The data is the site's own api/schemes.json, read through the static-asset binding once per
// isolate and kept: it changes only when the site is redeployed, which starts new isolates.
import { handleMcp } from "../site/mcp.mjs";

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

export async function onRequestPost({ request, env }) {
  let body;
  try {
    body = await request.json();
  } catch {
    return json({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "Parse error" } }, 400);
  }
  const d = await load(env, request);
  if (Array.isArray(body)) return json(body.map((r) => handleMcp(r, d)).filter(Boolean));
  const res = handleMcp(body, d);
  return res === null ? new Response(null, { status: 202, headers: CORS }) : json(res);
}
