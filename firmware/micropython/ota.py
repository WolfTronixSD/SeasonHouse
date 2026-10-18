# Wireless updates: upload a file over Wi-Fi, check it, then swap it in.
import os
import config

PROTECTED = ("main.py", "recovery.py")   # the safety net; replace only with force=1
ALLOWED_EXT = (".py", ".html", ".json", ".mpy", ".css", ".js")


def valid_name(name):
    if not name or name.startswith("/") or ".." in name or name.count("/") > 1:
        return False
    if "/" in name and not name.startswith("www/"):
        return False
    base = name.split("/")[-1]
    if not base or not any(base.endswith(e) for e in ALLOWED_EXT):
        return False
    return all(c.isalpha() or c.isdigit() or c in "_-." for c in base)


def check_key(key):
    return key == config.OTA_KEY and config.OTA_KEY != ""


def _exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def _syntax_error(path):
    """Return an error message if a .py file does not compile, else None."""
    try:
        with open(path) as f:
            compile(f.read(), path, "exec")
    except SyntaxError as e:
        return "syntax error: %s" % e
    except NameError:      # build without compile(): skip the check
        pass
    return None


async def receive(req, read_chunk):
    """Handle POST /api/ota?file=<name>&key=<OTA_KEY>[&force=1] with the file as the body."""
    name = req.arg("file")
    if not check_key(req.arg("key")):
        return 403, {"ok": False, "error": "wrong update key"}
    if not valid_name(name):
        return 400, {"ok": False, "error": "file name not allowed: %s" % name}
    if name in PROTECTED and req.arg("force") != "1":
        return 403, {"ok": False, "error": "%s is the safety net; add force=1 to replace it" % name}
    if "/" in name and not _exists("www"):
        os.mkdir("www")
    tmp = name + ".new"
    got = 0
    with open(tmp, "wb") as f:
        while got < req.length:
            chunk = await read_chunk(min(1024, req.length - got))
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
    if got != req.length:
        os.remove(tmp)
        return 400, {"ok": False, "error": "upload cut off (%d of %d bytes)" % (got, req.length)}
    if name.endswith(".py"):
        err = _syntax_error(tmp)
        if err:
            os.remove(tmp)
            return 400, {"ok": False, "error": "%s not installed, %s" % (name, err)}
    if _exists(name):
        os.remove(name)
    os.rename(tmp, name)
    print("OTA: installed", name, got, "bytes")
    return 200, {"ok": True, "file": name, "bytes": got}


def listing():
    out = []
    for d in ("", "www"):
        try:
            for n in os.listdir(d or "/"):
                p = (d + "/" + n) if d else n
                st = os.stat(p)
                if st[0] & 0x4000 == 0:      # skip directories
                    out.append({"file": p, "bytes": st[6]})
        except OSError:
            pass
    return out
