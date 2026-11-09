import { NextRequest, NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

const DISALLOWED_HEADERS = new Set([
  'host',
  'expect',
  'connection',
  'content-length',
  'transfer-encoding',
  'keep-alive',
]);

async function handleProxy(req: NextRequest, { params }: { params: { path: string[] } }) {
  const subpath = params?.path ? params.path.join('/') : '';
  const search = req.nextUrl.search || '';
  const backendBase = process.env.INTERNAL_BACKEND_URL || 'http://backend:8000';
  const targetUrl = `${backendBase}/api/${subpath}${search}`;

  try {
    const headers = new Headers();
    req.headers.forEach((value, key) => {
      const lower = key.toLowerCase();
      if (!DISALLOWED_HEADERS.has(lower)) {
        headers.set(key, value);
      }
    });

    const body = ['GET', 'HEAD'].includes(req.method) ? undefined : await req.arrayBuffer();

    const response = await fetch(targetUrl, {
      method: req.method,
      headers,
      body,
      signal: AbortSignal.timeout(60000),
    });

    const resHeaders = new Headers();
    response.headers.forEach((value, key) => {
      const lower = key.toLowerCase();
      if (!DISALLOWED_HEADERS.has(lower)) {
        resHeaders.set(key, value);
      }
    });

    const resBuffer = await response.arrayBuffer();
    return new NextResponse(resBuffer, {
      status: response.status,
      statusText: response.statusText,
      headers: resHeaders,
    });
  } catch (err: any) {
    console.error(`[API Proxy Error] Failed to proxy to ${targetUrl}:`, err);
    return NextResponse.json(
      { detail: `Proxy Error connecting to backend at ${backendBase}: ${err.message}` },
      { status: 502 }
    );
  }
}

export const GET = handleProxy;
export const POST = handleProxy;
export const PUT = handleProxy;
export const DELETE = handleProxy;
export const PATCH = handleProxy;
