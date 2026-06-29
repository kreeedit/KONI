"""Stdlib HTTP server for KONI. No external dependencies.

Routes:
  GET /                              -> index.html
  GET /static/<path>                 -> static assets (app.js, styles.css, fonts)
  GET /api/health                    -> {ok:true}
  GET /api/authors?q=&limit=          -> search result list
  GET /api/author/<aid>               -> one author + works
  GET /api/text/<aid>/<wid>/sections  -> section index for the reader
  GET /api/text/<aid>/<wid>/section/<idx> -> one section's blocks

Run:  python scripts/serve.py
"""
from __future__ import annotations

import json
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import canon
from . import repo
from . import texts
from . import sources
from . import flame_pure

STATIC_DIR = Path(__file__).resolve().parent / "static"


def _work_title(aid: str, wid: str) -> str:
    a = canon.canon().get(aid, {})
    w = a.get("works", {}).get(wid, {})
    return w.get("title_latin") or w.get("title_english") or w.get("title_greek") or f"{aid}.{wid}"


def _work_meta(aid: str, wid: str) -> dict:
    """Full academic metadata for a work (for the export)."""
    a = canon.canon().get(aid, {})
    w = a.get("works", {}).get(wid, {})
    return {
        "author_id": aid,
        "author_latin": a.get("author_name_latin"),
        "author_greek": a.get("author_name_greek"),
        "title_latin": w.get("title_latin"),
        "title_greek": w.get("title_greek"),
        "title_english": w.get("title_english"),
        "edition": w.get("edition"),
        "cts_urn": w.get("cts_urn"),
    }

_ROUTES = [
    (r"^/api/health$", "health"),
    (r"^/api/authors$", "authors"),
    (r"^/api/author/(\d{4})$", "author"),
    (r"^/api/text/(\d{4})/(\d{3})/sections$", "sections"),
    (r"^/api/text/(\d{4})/(\d{3})/section/(\d+)$", "section"),
    (r"^/api/sources/(\d{4})/(\d{3})$", "sources"),
    (r"^/api/compare_stream$", "compare_stream"),
    (r"^/api/compare$", "compare"),
]


class Handler(BaseHTTPRequestHandler):
    server_version = "KONI/0.1"

    # ---- helpers -----------------------------------------------------------
    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _static(self, rel: str):
        # safe path resolution under STATIC_DIR
        rel = unquote(rel)
        path = (STATIC_DIR / rel).resolve()
        try:
            path.relative_to(STATIC_DIR)
        except ValueError:
            self.send_error(403); return
        if not path.is_file():
            self.send_error(404); return
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", f"{ctype}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        # concise logging
        import sys
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    # ---- GET dispatch ------------------------------------------------------
    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        if path == "/" :
            return self._static("index.html")

        if path.startswith("/static/"):
            return self._static(path[len("/static/"):])

        for pat, name in _ROUTES:
            m = re.match(pat, path)
            if m:
                return self._dispatch(name, m, query)

        self.send_error(404, "Not found")

    def _dispatch(self, name, m, query):
        try:
            if name == "health":
                return self._json({"ok": True, "authors": len(canon.canon())})
            if name == "authors":
                q = query.get("q", "")
                limit = int(query.get("limit", "50"))
                return self._json(canon.search(q, limit))
            if name == "author":
                a = canon.get_author(m.group(1))
                if not a:
                    return self._json({"error": "not found"}, 404)
                return self._json(a)
            if name == "sections":
                aid, wid = m.group(1), m.group(2)
                return self._json(texts.sections(aid, wid))
            if name == "section":
                aid, wid = m.group(1), m.group(2)
                idx = int(m.group(3))
                sec = texts.section(aid, wid, idx)
                if sec is None:
                    return self._json({"error": "no text"}, 404)
                return self._json(sec)
            if name == "sources":
                aid, wid = m.group(1), m.group(2)
                return self._json(sources.discover(aid, wid))
            if name == "compare_stream":
                q = query
                a1, w1 = q.get("auth1", "").zfill(4), q.get("work1", "").zfill(3)
                a2, w2 = q.get("auth2", "").zfill(4), q.get("work2", "").zfill(3)
                if not (a1 and w1 and a2 and w2):
                    return self._json({"error": "auth1/work1/auth2/work2 required"}, 400)
                s1 = texts.section_texts(a1, w1)
                s2 = texts.section_texts(a2, w2)
                if s1 is None or s2 is None:
                    missing = []
                    if s1 is None: missing.append(f"{a1}.{w1}")
                    if s2 is None: missing.append(f"{a2}.{w2}")
                    return self._json(
                        {"error": "one or both works have no readable text: "
                                  + ", ".join(missing)}, 404)
                kw = {}
                ng = q.get("ngram", ""); no = q.get("n_out", ""); ch = q.get("chain", "")
                fz = q.get("fuzz", "")
                st = q.get("similarity_threshold", q.get("threshold", ""))
                if ng: kw["ngram"] = int(ng)
                if no: kw["n_out"] = int(no)
                if ch: kw["min_chain_words"] = int(ch)
                if fz != "": kw["fuzz_threshold"] = float(fz)
                if st != "": kw["similarity_threshold"] = float(st)
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Accel-Buffering", "no")
                self.end_headers()

                def _emit(obj):
                    self.wfile.write(
                        (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))
                    self.wfile.flush()

                try:
                    _emit({"t": "head",
                           "work1": {"aid": a1, "wid": w1,
                                     "title": _work_title(a1, w1),
                                     "meta": _work_meta(a1, w1)},
                           "work2": {"aid": a2, "wid": w2,
                                     "title": _work_title(a2, w2),
                                     "meta": _work_meta(a2, w2)}})
                    for ev in flame_pure.compare_iter(s1, s2, **kw):
                        _emit(ev)
                except (BrokenPipeError, ConnectionResetError):
                    return
                except Exception as exc:  # noqa: BLE001
                    try:
                        _emit({"t": "error", "error": str(exc)})
                    except Exception:
                        pass
                return

            if name == "compare":
                q = query
                a1, w1 = q.get("auth1", "").zfill(4), q.get("work1", "").zfill(3)
                a2, w2 = q.get("auth2", "").zfill(4), q.get("work2", "").zfill(3)
                if not (a1 and w1 and a2 and w2):
                    return self._json({"error": "auth1/work1/auth2/work2 required"}, 400)
                s1 = texts.section_texts(a1, w1)
                s2 = texts.section_texts(a2, w2)
                if s1 is None or s2 is None:
                    missing = []
                    if s1 is None: missing.append(f"{a1}.{w1}")
                    if s2 is None: missing.append(f"{a2}.{w2}")
                    return self._json(
                        {"error": "one or both works have no readable text: "
                                  + ", ".join(missing)}, 404)
                # live hyper-parameters (with safe defaults/clamps)
                ng = q.get("ngram", "")
                no = q.get("n_out", "")
                ch = q.get("chain", "")
                fz = q.get("fuzz", "")  # Levenshtein tolerance (Phase 2)
                vs = q.get("vocab", "")  # deprecated (BPE removed); ignored
                st = q.get("similarity_threshold", q.get("threshold", ""))
                kw = {}
                if ng: kw["ngram"] = int(ng)
                if no: kw["n_out"] = int(no)
                if ch: kw["min_chain_words"] = int(ch)
                if fz != "": kw["fuzz_threshold"] = float(fz)
                if st != "": kw["similarity_threshold"] = float(st)
                return self._json({
                    "work1": {"aid": a1, "wid": w1,
                              "title": _work_title(a1, w1),
                              "section_count": len(s1),
                              "meta": _work_meta(a1, w1)},
                    "work2": {"aid": a2, "wid": w2,
                              "title": _work_title(a2, w2),
                              "section_count": len(s2),
                              "meta": _work_meta(a2, w2)},
                    "result": flame_pure.compare(s1, s2, **kw),
                })
        except Exception as exc:  # noqa: BLE001
            return self._json({"error": str(exc)}, 500)


def run(host="127.0.0.1", port=8000):
    canon.load()
    # Preload the PerseusDL/canonical-greekLit repo map (builds + caches the
    # Greek-edition filename index; one GitHub tree fetch, cached on disk).
    repo.load()
    print(f"repo map: {len(repo.load())} Perseus Greek works indexed")
    srv = ThreadingHTTPServer((host, port), Handler)
    print(f"KONI reader on http://{host}:{port}/  (Ctrl-C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")


if __name__ == "__main__":
    run()