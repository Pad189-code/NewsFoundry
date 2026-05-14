import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailers",
  "transfer-encoding",
  "upgrade",
  "host",
]);

function resolveBackendBase(): string | null {
  const raw =
    process.env.BACKEND_PROXY_TARGET?.trim() || "http://127.0.0.1:8000";
  const base = raw.replace(/\/+$/, "");
  if (!/^https?:\/\//i.test(base)) {
    return null;
  }
  return base;
}

function copyHeaders(from: Headers, to: Headers) {
  from.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) {
      to.set(key, value);
    }
  });
}

async function proxy(
  request: NextRequest,
  pathSegments: string[] | undefined,
): Promise<NextResponse> {
  const base = resolveBackendBase();
  if (!base) {
    return NextResponse.json(
      {
        detail:
          "BACKEND_PROXY_TARGET doit être une URL absolue (https://…). " +
          "Ex. sur Vercel : variable d’environnement BACKEND_PROXY_TARGET = URL de l’API Railway.",
      },
      { status: 503 },
    );
  }

  const suffix =
    pathSegments && pathSegments.length > 0
      ? `/${pathSegments.join("/")}`
      : "";
  const target = new URL(`${base}${suffix}`);
  request.nextUrl.searchParams.forEach((value, key) => {
    target.searchParams.set(key, value);
  });

  const outHeaders = new Headers();
  copyHeaders(request.headers, outHeaders);

  const method = request.method.toUpperCase();
  let body: ArrayBuffer | undefined;
  if (!["GET", "HEAD"].includes(method)) {
    body = await request.arrayBuffer();
  }

  const upstream = await fetch(target, {
    method,
    headers: outHeaders,
    body: body && body.byteLength > 0 ? body : undefined,
    redirect: "manual",
  });

  const responseHeaders = new Headers();
  copyHeaders(upstream.headers, responseHeaders);

  return new NextResponse(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

type RouteCtx = { params: Promise<{ path?: string[] }> };

export async function GET(request: NextRequest, ctx: RouteCtx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function HEAD(request: NextRequest, ctx: RouteCtx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function POST(request: NextRequest, ctx: RouteCtx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function PUT(request: NextRequest, ctx: RouteCtx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function PATCH(request: NextRequest, ctx: RouteCtx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function DELETE(request: NextRequest, ctx: RouteCtx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}

export async function OPTIONS(request: NextRequest, ctx: RouteCtx) {
  const { path } = await ctx.params;
  return proxy(request, path);
}
