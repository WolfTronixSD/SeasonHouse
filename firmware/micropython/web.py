# A very small async HTTP server: enough for the control page, its JSON API
# and wireless updates.
from compat import asyncio, json


def unquote(s):
    s = s.replace("+", " ")
    out = bytearray()
    i = 0
    b = s.encode()
    while i < len(b):
        if b[i] == 37 and i + 2 < len(b):   # '%'
            out.append(int(b[i + 1:i + 3], 16))
            i += 3
        else:
            out.append(b[i])
            i += 1
    return out.decode()


def parse_query(qs):
    q = {}
    for part in qs.split("&"):
        if part:
            k, _, v = part.partition("=")
            q[unquote(k)] = unquote(v)
    return q


class Request:
    def __init__(self, method, path, query, headers, reader):
        self.method = method
        self.path = path
        self.query = query
        self.headers = headers
        self.reader = reader
        self.length = int(headers.get("content-length", "0") or 0)

    def arg(self, name, default=""):
        return self.query.get(name, default)


REASONS = {200: "OK", 400: "Bad Request", 403: "Forbidden", 404: "Not Found", 409: "Conflict", 500: "Error"}


class Server:
    def __init__(self):
        self.routes = {}

    def route(self, path):
        def deco(fn):
            self.routes[path] = fn
            return fn
        return deco

    async def _send(self, writer, status, ctype, body):
        if isinstance(body, str):
            body = body.encode()
        writer.write(("HTTP/1.1 %d %s\r\nContent-Type: %s\r\nContent-Length: %d\r\n"
                     "Cache-Control: no-store\r\nConnection: close\r\n\r\n" % (status, REASONS.get(status, ""), ctype, len(body))).encode())
        writer.write(body)
        await writer.drain()

    async def _send_file(self, writer, path, ctype):
        import os
        size = os.stat(path)[6]
        writer.write(("HTTP/1.1 200 OK\r\nContent-Type: %s\r\nContent-Length: %d\r\nConnection: close\r\n\r\n" % (ctype, size)).encode())
        buf = bytearray(1024)
        with open(path, "rb") as f:
            while True:
                n = f.readinto(buf)
                if not n:
                    break
                writer.write(buf[:n] if n < len(buf) else buf)
                await writer.drain()

    async def _handle(self, reader, writer):
        try:
            line = await asyncio.wait_for(reader.readline(), 5)
            parts = line.decode().split()
            if len(parts) < 2:
                return
            method, target = parts[0], parts[1]
            headers = {}
            while True:
                h = await asyncio.wait_for(reader.readline(), 5)
                if h in (b"\r\n", b"\n", b""):
                    break
                k, _, v = h.decode().partition(":")
                headers[k.strip().lower()] = v.strip()
            path, _, qs = target.partition("?")
            req = Request(method, path, parse_query(qs), headers, reader)
            fn = self.routes.get(path)
            if fn is None:
                await self._send(writer, 404, "text/plain", "Nothing here but cobwebs.")
                return
            res = fn(req)
            if hasattr(res, "send"):      # coroutine
                res = await res
            if res[0] == "file":
                await self._send_file(writer, res[1], res[2])
            elif isinstance(res[1], (dict, list)):
                await self._send(writer, res[0], "application/json", json.dumps(res[1]))
            else:
                await self._send(writer, res[0], res[2] if len(res) > 2 else "text/plain", res[1])
        except Exception as e:
            print("HTTP error:", e)
            try:
                await self._send(writer, 500, "text/plain", "Error: %s" % e)
            except Exception:
                pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def start(self, port=80):
        return await asyncio.start_server(self._handle, "0.0.0.0", port)
