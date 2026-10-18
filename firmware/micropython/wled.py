# Recalls a WLED preset with a tiny non-blocking HTTP POST to /json/state.
from compat import asyncio


async def preset(host, ps):
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, 80), 2)
        body = '{"on":true,"ps":%d}' % ps
        writer.write(("POST /json/state HTTP/1.1\r\nHost: %s\r\nContent-Type: application/json\r\n"
                      "Content-Length: %d\r\nConnection: close\r\n\r\n%s") % (host, len(body), body))
        await writer.drain()
        status = await asyncio.wait_for(reader.readline(), 2)
        writer.close()
        await writer.wait_closed()
        print("WLED preset", ps, status[9:12])
    except Exception as e:
        print("WLED unreachable:", e)
