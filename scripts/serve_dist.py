"""Serve dist/ the way Cloudflare Pages does, for CI and local browser tests.
/map, /map/ and /map/<slug> -> map.html; /<path> -> <path>.html when it exists; / with map-state
params (r, veh, lat, lon, z, paid) -> 302 /map?... (same rule as functions/index.js).
Usage: python3 scripts/serve_dist.py [port] [dir]   (defaults 8765, dist)"""
import http.server, os, sys, urllib.parse

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
DIR = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist")
MAP_PARAMS = {"r", "veh", "lat", "lon", "z", "paid"}


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=DIR, **k)

    def log_message(self, *a): pass

    def do_GET(self):
        u = urllib.parse.urlsplit(self.path); p = u.path
        if p == "/" and MAP_PARAMS & set(urllib.parse.parse_qs(u.query)):
            self.send_response(302); self.send_header("Location", "/map?" + u.query); self.end_headers(); return
        if p == "/map" or p.startswith("/map/"): p = "/map.html"
        elif p != "/" and "." not in p.rsplit("/", 1)[-1]:
            q = p.rstrip("/") + ".html"
            if os.path.isfile(os.path.join(DIR, q.lstrip("/"))): p = q
        self.path = p + ("?" + u.query if u.query else "")
        return super().do_GET()


if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("", PORT), H).serve_forever()
