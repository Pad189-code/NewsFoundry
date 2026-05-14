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

/** En-têtes à ne pas relayer vers le backend (Node recalcule Content-Length ; le reste évite les conflits Vercel → fetch). */
const STRIP_REQUEST = new Set([
  ...HOP_BY_HOP,
  "content-length",
  "accept-encoding",
  "x-forwarded-for",
  "x-forwarded-host",
  "x-forwarded-port",
  "x-forwarded-proto",
  "x-real-ip",
  "x-vercel-id",
  "x-vercel-forwarded-for",
  "x-vercel-deployment-url",
  "x-vercel-proxied-for",
  "x-vercel-ja4-digest",
  "x-invoke-path",
  "x-invoke-query",
  "x-middleware-invoke",
  "x-middleware-subrequest",
  "next-url",
  "x-nextjs-data",
  "x-open-next",
]);

/** En-têtes de réponse amont à ne pas renvoyer au navigateur (corps déjà décompressé par fetch). */
const STRIP_RESPONSE = new Set([
  ...HOP_BY_HOP,
  "content-encoding",
  "content-length",
  "transfer-encoding",
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

function filterRequestHeaders(from: Headers): Headers {
  const to = new Headers();
  from.forEach((value, key) => {
    if (!STRIP_REQUEST.has(key.toLowerCase())) {
      to.set(key, value);
    }
  });
  return to;
}

function filterResponseHeaders(from: Headers): Headers {
  const to = new Headers();
  from.forEach((value, key) => {
    if (!STRIP_RESPONSE.has(key.toLowerCase())) {
      to.append(key, value);
    }
  });
  return to;
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
  let target: URL;
  try {
    target = new URL(`${base}${suffix}`);
    request.nextUrl.searchParams.forEach((value, key) => {
      target.searchParams.set(key, value);
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { detail: `URL proxy invalide : ${message}` },
      { status: 400 },
    );
  }

  const method = request.method.toUpperCase();
  let body: ArrayBuffer | undefined;
  if (!["GET", "HEAD"].includes(method)) {
    body = await request.arrayBuffer();
  }

  const outHeaders = filterRequestHeaders(request.headers);

  try {
    const upstream = await fetch(target, {
      method,
      headers: outHeaders,
      body: body && body.byteLength > 0 ? body : undefined,
      redirect: "manual",
    });

    const responseHeaders = filterResponseHeaders(upstream.headers);
    const payload = await upstream.arrayBuffer();

    return new NextResponse(payload, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      {
        detail:
          `Échec du proxy vers le backend (${target.origin}). ` +
          `Vérifiez BACKEND_PROXY_TARGET et que l’API répond en HTTPS. Détail : ${message}`,
      },
      { status: 502 },
    );
  }
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
