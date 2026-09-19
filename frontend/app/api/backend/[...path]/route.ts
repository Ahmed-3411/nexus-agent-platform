import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

type RouteContext = { params: Promise<{ path: string[] }> };

async function proxy(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  const backend = process.env.BACKEND_URL || "http://localhost:8000";
  const query = request.nextUrl.search;
  const headers = new Headers();
  const authorization = request.headers.get("authorization");
  const contentType = request.headers.get("content-type");
  if (authorization) headers.set("Authorization", authorization);
  if (contentType) headers.set("Content-Type", contentType);

  const hasBody = request.method !== "GET" && request.method !== "HEAD";
  try {
    const response = await fetch(`${backend}/${path.join("/")}${query}`, {
      method: request.method,
      headers,
      body: hasBody ? await request.text() : undefined,
      cache: "no-store",
    });
    return new Response(response.body, {
      status: response.status,
      headers: { "Content-Type": response.headers.get("content-type") || "application/json" },
    });
  } catch {
    return Response.json({ detail: "Backend service is unavailable." }, { status: 502 });
  }
}

export const GET = proxy;
export const POST = proxy;
