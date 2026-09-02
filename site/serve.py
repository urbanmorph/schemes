"""
Local static server with gzip. 127.0.0.1 only — this deploys nothing.

`python -m http.server` sends no compression, which made the index look far heavier
than it is: the page is 1.76 MB of highly repetitive markup and compresses to roughly a
seventh of that. Any real host would gzip it, so serving it uncompressed locally gives a
misleading picture of the only number that matters to a reader — what actually crosses
the wire.
"""

import argparse
import functools
import gzip
import http.server
import io
import os
import socketserver

COMPRESS = (".html", ".css", ".js", ".json", ".svg", ".txt", ".csv")
MIN_BYTES = 1024


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # The stylesheet URL is content-hashed, so it is safe to cache hard. HTML is
        # rebuilt in place and must revalidate, or an edit appears not to have landed.
        path = self.path.split("?")[0]
        if path.endswith(".css") and "v=" in self.path:
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        else:
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def send_head(self):
        path = self.translate_path(self.path)
        # Extensionless URLs, because Cloudflare Pages serves foo.html at /foo and the
        # site's links are written that way. Without this the local preview 404s on every
        # link the deployed site resolves, which is the worst kind of difference between
        # development and production: the one that only shows up in production.
        #
        # self.path is rewritten, not just the local variable: every fall-through below
        # calls super().send_head(), which re-derives the path from self.path and would
        # hand back the 404 this is meant to avoid. Rewriting a local looked correct and
        # 404ed on every scheme page.
        if not os.path.exists(path) and not path.endswith("/"):
            if os.path.isfile(path + ".html"):
                path += ".html"
                head, sep, tail = self.path.partition("?")
                self.path = head + ".html" + sep + tail
        if os.path.isdir(path):
            # Resolve the directory index BEFORE deciding on compression. Falling through
            # to the parent handler here meant "/" — the single heaviest page on the
            # site — was the one path that never got gzipped.
            if not self.path.endswith("/"):
                return super().send_head()      # let it issue the redirect
            index = os.path.join(path, "index.html")
            if not os.path.isfile(index):
                return super().send_head()      # directory listing
            path = index
        wants_gzip = "gzip" in self.headers.get("Accept-Encoding", "")
        if not (wants_gzip and path.endswith(COMPRESS) and os.path.isfile(path)):
            return super().send_head()
        try:
            raw = open(path, "rb").read()
        except OSError:
            return super().send_head()
        if len(raw) < MIN_BYTES:
            return super().send_head()

        body = gzip.compress(raw, 6)
        self.send_response(200)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Vary", "Accept-Encoding")
        self.end_headers()
        return io.BytesIO(body)

    def log_message(self, fmt, *args):
        pass            # the build output is the interesting log, not every asset hit


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    ap = argparse.ArgumentParser(description="Serve site/_out locally, with gzip.")
    ap.add_argument("--port", type=int, default=8788)
    ap.add_argument("--dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "_out"))
    a = ap.parse_args()
    handler = functools.partial(Handler, directory=a.dir)
    with Server(("127.0.0.1", a.port), handler) as httpd:
        print(f"serving {a.dir} at http://127.0.0.1:{a.port}/  (gzip on, ctrl-c to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nstopped")


if __name__ == "__main__":
    main()
