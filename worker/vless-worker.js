import { connect } from 'cloudflare:sockets';

const DEFAULT_UUID = '408f6245-caf9-4432-81c5-e337ebc479c0';
const CONFIG_NAME = 'Family-Worker';

export default {
  async fetch(request, env) {
    const uuid = env.UUID || DEFAULT_UUID;
    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, '') || '/';

    if (path === '/' && request.method === 'GET') {
      return new Response(infoPage(url.host, uuid), {
        headers: { 'content-type': 'text/html; charset=utf-8' },
      });
    }

    if (path === '/cfg' && request.method === 'GET') {
      return textResponse(buildUri(url.host, uuid, CONFIG_NAME));
    }

    if (path === '/sub' && request.method === 'GET') {
      return textResponse(btoa(buildUri(url.host, uuid, CONFIG_NAME)));
    }

    if (request.headers.get('upgrade') === 'websocket') {
      const expected = '/' + uuid;
      if (path !== expected) return new Response('not found', { status: 404 });
      return await handleVless(request, uuid.replace(/-/g, ''));
    }

    return new Response('not found', { status: 404 });
  },
};

function textResponse(body) {
  return new Response(body + '\n', {
    headers: {
      'content-type': 'text/plain; charset=utf-8',
      'access-control-allow-origin': '*',
    },
  });
}

function buildUri(host, uuid, name) {
  const p = new URLSearchParams({
    encryption: 'none',
    security: 'tls',
    sni: host,
    type: 'ws',
    host: host,
    path: '/' + uuid,
  });
  return 'vless://' + uuid + '@' + host + ':443?' + p.toString() + '#' + encodeURIComponent(name);
}

function infoPage(host, uuid) {
  return `<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>سرور خانوادگی</title></head>
<body style="font-family:sans-serif;max-width:40rem;margin:2rem auto;padding:0 1rem;line-height:1.8">
<h2>✅ سرور فعال است</h2>
<p>کانفیگ با این آدرس در دسترس است:</p>
<p><code style="word-break:break-all">https://${host}/cfg</code></p>
<p style="color:#666">UUID: <code>${uuid}</code></p>
</body></html>`;
}

async function handleVless(request, expectedUuidHex) {
  const wsPair = new WebSocketPair();
  const client = wsPair[0];
  const server = wsPair[1];

  server.accept();

  let remoteWriter = null;
  let headerDone = false;
  let pending = readEarlyData(request);

  server.addEventListener('message', async (event) => {
    try {
      if (headerDone) {
        await remoteWriter?.write(event.data);
        return;
      }

      pending = concat(pending, new Uint8Array(event.data));
      if (pending.length < 25) return;

      const parsed = parseHeader(pending, expectedUuidHex);
      if (parsed.hasError) {
        server.close(1008, 'bad request');
        return;
      }

      headerDone = true;
      const tcp = connect(
        { hostname: parsed.remoteAddress, port: parsed.remotePort },
        { allowHalfOpen: false },
      );
      await tcp.opened;

      remoteWriter = tcp.writable.getWriter();
      await remoteWriter.write(parsed.payload);

      server.send(new Uint8Array([0x00, 0x00]));

      pumpRemoteToWs(tcp, server).catch(() => closeAll(tcp, server));
    } catch (err) {
      closeAll(null, server);
    }
  });

  server.addEventListener('close', () => {
    try { remoteWriter?.releaseLock(); } catch (e) {}
  });
  server.addEventListener('error', () => {});

  return new Response(null, { status: 101, webSocket: client });
}

async function pumpRemoteToWs(tcp, server) {
  const reader = tcp.readable.getReader();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    if (server.readyState === 1) server.send(value);
  }
  closeAll(tcp, server);
}

function readEarlyData(request) {
  const proto = request.headers.get('sec-websocket-protocol');
  if (!proto) return new Uint8Array(0);
  try {
    return base64UrlDecode(proto.split(',')[0].trim());
  } catch (e) {
    return new Uint8Array(0);
  }
}

function base64UrlDecode(b64) {
  const s = b64.replace(/-/g, '+').replace(/_/g, '/');
  const bin = atob(s + '='.repeat((4 - (s.length % 4)) % 4));
  return Uint8Array.from(bin, (c) => c.charCodeAt(0));
}

function concat(a, b) {
  const out = new Uint8Array(a.length + b.length);
  out.set(a);
  out.set(b, a.length);
  return out;
}

function parseHeader(buf, expectedUuidHex) {
  if (buf[0] !== 0x00) return { hasError: true };

  const uuidHex = [...buf.slice(2, 18)]
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
  if (uuidHex !== expectedUuidHex) return { hasError: true };

  const optLen = buf[18];
  const cmd = buf[19 + optLen];
  if (cmd !== 1) return { hasError: true };

  const port = (buf[20 + optLen] << 8) | buf[21 + optLen];
  const atype = buf[22 + optLen];
  let addr;
  let offset;

  if (atype === 1) {
    addr = [...buf.slice(23 + optLen, 27 + optLen)].join('.');
    offset = 27 + optLen;
  } else if (atype === 2) {
    const len = buf[23 + optLen];
    addr = new TextDecoder().decode(buf.slice(24 + optLen, 24 + optLen + len));
    offset = 24 + optLen + len;
  } else if (atype === 3) {
    const parts = [];
    for (let i = 0; i < 8; i++) {
      parts.push(((buf[23 + optLen + i * 2] << 8) | buf[24 + optLen + i * 2]).toString(16));
    }
    addr = parts.join(':');
    offset = 39 + optLen;
  } else {
    return { hasError: true };
  }

  return {
    hasError: false,
    remoteAddress: addr,
    remotePort: port,
    payload: buf.slice(offset),
  };
}

function closeAll(tcp, server) {
  try { tcp?.close(); } catch (e) {}
  try { server?.close(); } catch (e) {}
}
