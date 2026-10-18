#!/usr/bin/env python3
"""Upload firmware to an installed prop over Wi-Fi, no cable needed.

    python3 tools/ota_push.py spider.local --key YOUR_OTA_KEY            # everything
    python3 tools/ota_push.py 192.168.1.80 --key K app.py www/index.html  # just these
    python3 tools/ota_push.py storm.local --prop lightning --key K       # another prop

Files are the prop's set from tools/stage_prop.py (shared modules plus the
prop's own folder). The prop checks each .py file compiles before installing
it, then reboots when all files are in.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stage_prop  # noqa: E402

SKIP = {"main.py", "recovery.py", "settings.json"}   # safety net and your saved settings


def all_files(prop):
    out = [rel for rel in stage_prop.files(prop) if rel not in SKIP]
    return sorted(out, key=lambda r: (r == "app.py", r))   # app.py last: it imports the rest


def call(url, data=None):
    req = urllib.request.Request(url, data=data, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b'{"ok": false, "error": "HTTP %d"}' % e.code)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("host", help="prop address, e.g. spider.local or 192.168.1.80")
    ap.add_argument("--key", required=True, help="OTA_KEY from config.py")
    ap.add_argument("--prop", default="spider", choices=stage_prop.props(), help="which prop (default spider)")
    ap.add_argument("--no-reboot", action="store_true")
    ap.add_argument("--force", action="store_true", help="also allow replacing main.py / recovery.py")
    ap.add_argument("files", nargs="*", help="file names on the prop, e.g. app.py www/index.html (default: all)")
    a = ap.parse_args()
    base = "http://%s" % a.host
    sources = stage_prop.files(a.prop)
    files = a.files or all_files(a.prop)
    failed = 0
    for rel in files:
        if rel not in sources:
            sys.exit("%s is not one of the %s files" % (rel, a.prop))
        with open(sources[rel], "rb") as f:
            data = f.read()
        q = urllib.parse.urlencode({"file": rel, "key": a.key, "force": "1" if a.force else "0"})
        res = call("%s/api/ota?%s" % (base, q), data)
        if res.get("ok"):
            print("  %-22s %6d bytes  ok" % (rel, res["bytes"]))
        else:
            failed += 1
            print("  %-22s FAILED: %s" % (rel, res.get("error")))
    if failed:
        print("%d file(s) failed; not rebooting. The prop is still running its old code." % failed)
        sys.exit(1)
    if not a.no_reboot:
        call("%s/api/reboot?%s" % (base, urllib.parse.urlencode({"key": a.key})))
        print("Rebooting. The control page is back in about 10 seconds.")


if __name__ == "__main__":
    main()
