"""Minimal form-collection server (standard library only).

Run:  python server.py
Then open http://localhost:8000/ in your browser.

Submissions are appended to submissions.csv in this same folder.
"""

import csv
import json
import os
import re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
FORM_FILE = os.path.join(HERE, "contact-form.html")
DATA_FILE = os.path.join(HERE, "submissions.csv")
FIELDS = ["timestamp", "firstName", "lastName", "email"]

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
HOST, PORT = "localhost", 8000


def save_submission(record):
    """Append one record to the CSV, writing a header row if the file is new."""
    new_file = not os.path.exists(DATA_FILE)
    with open(DATA_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(record)


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html", "/contact-form.html"):
            try:
                with open(FORM_FILE, "rb") as f:
                    body = f.read()
            except FileNotFoundError:
                self.send_error(404, "contact-form.html not found")
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404, "Not found")

    def do_POST(self):
        if self.path != "/submit":
            self.send_error(404, "Not found")
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self._send_json(400, {"ok": False, "error": "Invalid JSON."})
            return

        first = str(data.get("firstName", "")).strip()
        last = str(data.get("lastName", "")).strip()
        email = str(data.get("email", "")).strip()

        if not first or not last or not email:
            self._send_json(400, {"ok": False, "error": "All fields are required."})
            return
        if not EMAIL_RE.match(email):
            self._send_json(400, {"ok": False, "error": "Invalid email address."})
            return

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "firstName": first,
            "lastName": last,
            "email": email,
        }
        save_submission(record)
        self._send_json(200, {"ok": True, "message": "Submission saved."})

    def log_message(self, fmt, *args):
        # Keep the console output concise.
        print("%s - %s" % (self.address_string(), fmt % args))


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Serving form at http://{HOST}:{PORT}/")
    print(f"Saving submissions to {DATA_FILE}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
