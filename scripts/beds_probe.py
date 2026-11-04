"""Probe candidate real rain and fire recordings: read each item's licence from its own page, download the
preview, and let earshot judge it. Writes probe/report.md for a human (or Claude) to pick from.

Runs in CI (.github/workflows/beds.yml) because the dev sandbox can't reach these sites. Nothing here is used by
the pipeline until an item is written into assets/ambience/beds.json with its licence.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

UA = {"User-Agent": "facepipe-beds-probe/1.0"}
FREESOUND = {"rain": [212580, 346642, 648529, 752099, 575464],
             "fire": [263994, 414767, 800660, 545637, 650574]}
MIXKIT = {"rain": "https://mixkit.co/free-sound-effects/rain/", "fire": "https://mixkit.co/free-sound-effects/fire/"}
ALLOWED = re.compile(r"publicdomain/zero|licenses/by/[234]\.0")


def get(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def freesound(kind: str, sid: int) -> dict:
    page = f"https://freesound.org/s/{sid}/"
    try:
        html = get(page)
    except Exception as e:  # noqa: BLE001
        return {"kind": kind, "source": "freesound", "id": sid, "page": page, "error": str(e)}
    lic = sorted(set(re.findall(r"creativecommons\.org/(?:licenses|publicdomain)/[a-z\-]+/[0-9.]+", html)))
    prev = re.search(r"https://cdn\.freesound\.org/previews/\d+/%d_\d+-hq\.(?:ogg|mp3)" % sid, html)
    title = re.search(r"<title>(.*?)</title>", html, re.S)
    return {"kind": kind, "source": "freesound", "id": sid, "page": page, "licence_links": lic,
            "allowed": bool(lic) and all(ALLOWED.search(x) for x in lic),
            "title": title[1].strip() if title else "", "audio": prev[0] if prev else None}


def mixkit(kind: str, url: str) -> list[dict]:
    try:
        html = get(url)
    except Exception as e:  # noqa: BLE001
        return [{"kind": kind, "source": "mixkit", "page": url, "error": str(e)}]
    out = []
    for m in re.finditer(r"https://assets\.mixkit\.co/active_storage/sfx/(\d+)/\1(?:-preview)?\.(?:mp3|wav)", html):
        sid = m[1]
        before = html[max(0, m.start() - 3000): m.start()]
        titles = re.findall(r">\s*([A-Z][^<>]{3,60}?)\s*</", before)
        out.append({"kind": kind, "source": "mixkit", "id": int(sid), "page": url, "title": titles[-1] if titles else "",
                    "licence_links": ["Mixkit Sound Effects Free License (site-wide, stated on the page)"]
                    if "Mixkit License" in html else [], "allowed": "Mixkit License" in html,
                    "audio": f"https://assets.mixkit.co/active_storage/sfx/{sid}/{sid}.wav"})
    seen, uniq = set(), []
    for o in out:
        if o["id"] not in seen:
            seen.add(o["id"])
            uniq.append(o)
    return uniq


def earshot(path: Path) -> str:
    res = []
    for cmd in (["realness"], ["describe"], ["measure"]):
        r = subprocess.run(["earshot", *cmd, str(path)], capture_output=True, text=True, timeout=600)
        res.append((r.stdout or r.stderr).strip().splitlines()[0] if (r.stdout or r.stderr) else "")
    return "\n".join(res)


def main(out: Path = Path("probe")) -> None:
    out.mkdir(exist_ok=True)
    items = [freesound(k, i) for k, ids in FREESOUND.items() for i in ids]
    items += [x for k, u in MIXKIT.items() for x in mixkit(k, u)]
    report = ["# Real rain and fire candidates", ""]
    for it in items:
        it["file"] = None
        if it.get("allowed") and it.get("audio"):
            f = out / f"{it['source']}-{it['id']}{Path(it['audio']).suffix}"
            try:
                req = urllib.request.Request(it["audio"], headers=UA)
                f.write_bytes(urllib.request.urlopen(req, timeout=120).read())
                it["file"] = str(f)
                it["earshot"] = earshot(f)
            except Exception as e:  # noqa: BLE001
                it["error"] = f"download: {e}"
        report += [f"## {it['kind']} {it['source']} {it.get('id')} {it.get('title', '')}",
                   f"- page: {it.get('page')}", f"- licence: {it.get('licence_links')} allowed={it.get('allowed')}",
                   f"- audio: {it.get('audio')}", f"- error: {it.get('error', '')}", "```", it.get("earshot", ""), "```", ""]
    (out / "items.json").write_text(json.dumps(items, indent=2))
    (out / "report.md").write_text("\n".join(report))
    print("\n".join(report))


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("probe"))
