"""Start the KONI server for testing without the network-bound Perseus repo
preload (this sandbox has no outbound network, so repo.load() would block)."""
import os, sys
sys.path.insert(0, os.getcwd())
sys.path.insert(0, "scripts")
from http.server import ThreadingHTTPServer
from app import server, canon, repo

canon.load()
repo.load = lambda *a, **k: {}          # keep startup offline
port = int(sys.argv[1] if len(sys.argv) > 1 else 8731)
srv = ThreadingHTTPServer(("127.0.0.1", port), server.Handler)
print("listening on", port, flush=True)
srv.serve_forever()
