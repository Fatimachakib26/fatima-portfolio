"""Étape 1 – Acquisition : télécharger la source officielle et prouver son intégrité.

Produit data/raw/MANIFEST.json : URL, date de téléchargement, taille, empreinte SHA-256,
nombre de lignes et de colonnes. Le fichier brut n'est JAMAIS modifié ensuite.
"""
from __future__ import annotations

import csv
import hashlib
import json
import urllib.request
from datetime import datetime, timezone

from .config import RAW, SOURCE


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "credit-horizon-data-pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=600) as r, open(dest, "wb") as out:
        expected = int(r.headers.get("Content-Length") or 0)
        n = 0
        for chunk in iter(lambda: r.read(1 << 20), b""):
            out.write(chunk)
            n += len(chunk)
    if expected and n != expected:
        raise IOError(f"Téléchargement incomplet de {url} : {n} octets reçus sur {expected}")


def count_rows(path) -> tuple[int, int]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        return sum(1 for _ in reader), len(header)


def run(force: bool = False) -> dict:
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = {"source": {k: v for k, v in SOURCE.items() if k != "files"}, "files": {}}
    for key, meta in SOURCE["files"].items():
        dest = RAW / meta["name"]
        if force or not dest.exists():
            print(f"  téléchargement {meta['url']}")
            download(meta["url"], dest)
        entry = {**meta, "bytes": dest.stat().st_size, "sha256": sha256(dest),
                 "downloaded_at": datetime.fromtimestamp(dest.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")}
        if dest.suffix == ".csv":
            entry["rows"], entry["columns"] = count_rows(dest)
        manifest["files"][key] = entry
    (RAW / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def verify() -> None:
    """Contrôle d'intégrité : le fichier local est-il exactement celui du manifeste ?"""
    manifest = json.loads((RAW / "MANIFEST.json").read_text(encoding="utf-8"))
    for key, e in manifest["files"].items():
        got = sha256(RAW / e["name"])
        if got != e["sha256"]:
            raise ValueError(f"{e['name']} : empreinte {got} différente du manifeste {e['sha256']}")
    print("  intégrité vérifiée (SHA-256 conforme au manifeste)")
