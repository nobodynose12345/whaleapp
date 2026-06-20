#!/usr/bin/env python3
"""WhaleApp – minimal HTTP server (stdlib only)."""

from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "0.0.0.0"
PORT = 8080


class WhaleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            body = b"Hello from WhaleApp\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):  # quieter logs
        print(f"[WhaleApp] {self.address_string()} – {fmt % args}")


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), WhaleHandler)
    print(f"[WhaleApp] Listening on http://{HOST}:{PORT}  (Ctrl-C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[WhaleApp] Shutting down.")
        server.server_close()
