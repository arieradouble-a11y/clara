import { NextRequest } from "next/server";

// Forward /api/clara/<path> to the Clara FastAPI backend. Keeps the browser on a
// single origin and lets the Python engine stay where it is.
const BASE = process.env.CLARA_API ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

async function proxy(req: NextRequest, path: string[]): Promise<Response> {
  const target = `${BASE}/${path.join("/")}`;
  const reqHeaders: Record<string, string> = { "content-type": "application/json" };
  const auth = req.headers.get("authorization");
  if (auth) reqHeaders["authorization"] = auth; // forward the bearer token
  const init: RequestInit = { method: req.method, headers: reqHeaders };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.text();
  }
  const upstream = await fetch(target, init);
  const buffer = await upstream.arrayBuffer();
  const respHeaders: Record<string, string> = {
    "content-type": upstream.headers.get("content-type") ?? "application/json",
  };
  const disposition = upstream.headers.get("content-disposition");
  if (disposition) respHeaders["content-disposition"] = disposition;
  return new Response(buffer, { status: upstream.status, headers: respHeaders });
}

type Ctx = { params: { path: string[] } };

export async function GET(req: NextRequest, ctx: Ctx): Promise<Response> {
  return proxy(req, ctx.params.path);
}

export async function POST(req: NextRequest, ctx: Ctx): Promise<Response> {
  return proxy(req, ctx.params.path);
}
