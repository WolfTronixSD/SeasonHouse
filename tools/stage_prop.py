#!/usr/bin/env python3
"""Put together the files for one prop, ready to copy to its ESP32.

    python3 tools/stage_prop.py lightning          # -> build/lightning/
    cd build/lightning && mpremote cp -r . : + reset

Props: spider (the ceiling prop), lightning, screamometer, cauldron, rat.
Each prop = the shared modules in firmware/micropython/ plus its own folder
in firmware/props/<prop>/ (app.py, config.py, www/index.html, ...), whose files
win when a name exists in both.
"""
import argparse
import os
import shutil

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SHARED = os.path.join(ROOT, "firmware", "micropython")
PROPS = os.path.join(ROOT, "firmware", "props")
SPIDER_ONLY = {"app.py", "config.py", "fx.py", "seasons.json", "www"}


def props():
    return ["spider"] + sorted(d for d in os.listdir(PROPS) if os.path.isdir(os.path.join(PROPS, d)))


def files(prop):
    """{relative name: source path} for every file the prop needs."""
    out = {}
    for f in os.listdir(SHARED):
        src = os.path.join(SHARED, f)
        if f.startswith((".", "__")) or f == "settings.json":
            continue
        if prop != "spider" and f in SPIDER_ONLY:
            continue
        if os.path.isdir(src):
            for g in os.listdir(src):
                out[f + "/" + g] = os.path.join(src, g)
        else:
            out[f] = src
    if prop != "spider":
        base = os.path.join(PROPS, prop)
        if not os.path.isdir(base):
            raise SystemExit("unknown prop %r, pick one of: %s" % (prop, ", ".join(props())))
        for dirpath, dirs, names in os.walk(base):
            dirs[:] = [d for d in dirs if not d.startswith((".", "__"))]
            for n in names:
                if n.startswith(".") or n == "settings.json":
                    continue
                src = os.path.join(dirpath, n)
                out[os.path.relpath(src, base).replace(os.sep, "/")] = src
    return out


def stage(prop, out=None):
    out = out or os.path.join(ROOT, "build", prop)
    if os.path.isdir(out):
        shutil.rmtree(out)
    for rel, src in files(prop).items():
        dst = os.path.join(out, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(src, dst)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prop", choices=props())
    ap.add_argument("--out", help="folder to fill (default build/<prop>)")
    a = ap.parse_args()
    path = stage(a.prop, a.out)
    print("%d files in %s" % (len(files(a.prop)), os.path.relpath(path)))
    print("Copy them to the ESP32 with:  cd %s && mpremote cp -r . : + reset" % os.path.relpath(path))
