#!/usr/bin/env python3
"""Fake story service for the base-camp-failure-lab quest.

A small web server on this machine only (127.0.0.1). It holds 100 made-up
stories and hands them out 20 to a page:

    GET /stories?page=1   ...   GET /stories?page=5

A healthy answer is JSON:

    {"total": 100, "page": 1, "next": 2, "items": [{"id": "STORY-001", "title": "Story 001"}, ...]}

"total" is the service's own count of all stories. "next" is the next page
number, or null on the last page.

It can be told to fail on purpose. The failure is chosen when it starts:

    --fail none            every page is healthy
    --fail timeout         the failing page gets no answer for --hang seconds
    --fail partial         the failing page looks like a clean last page:
                           status 200, its 20 items, "next": null, and
                           "total" still 100
    --fail rate-limit      the failing page gets status 429 and a Retry-After
                           header of --retry-after seconds
    --fail malformed       the failing page's answer is cut off part-way, so
                           it is not JSON
    --fail malformed-item  the failing page is good JSON, but one item has
                           no "id"

    --page N     which page fails (default 3)
    --times N    how many requests for that page fail before it turns healthy
                 (default 0, meaning it fails every time)

It makes no outgoing requests and writes no files. Each request is printed as
one line so a run can be read afterwards.

Usage: fake_service.py [--port 8799] [--fail MODE] [--page N] [--times N]
                       [--hang SECONDS] [--retry-after SECONDS]
"""
import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

TOTAL = 100
PAGE_SIZE = 20
LAST_PAGE = TOTAL // PAGE_SIZE
MODES = ["none", "timeout", "partial", "rate-limit", "malformed", "malformed-item"]


def page_items(page):
    first = (page - 1) * PAGE_SIZE + 1
    return [{"id": "STORY-%03d" % n, "title": "Story %03d" % n} for n in range(first, first + PAGE_SIZE)]


class Handler(BaseHTTPRequestHandler):
    opts = None
    hits = 0  # requests seen for the failing page
    lock = threading.Lock()

    def log_message(self, fmt, *args):  # replace the default access log
        pass

    def note(self, text):
        print("service: page %s -> %s" % (self.page, text), flush=True)

    def send_json_text(self, status, text, headers=()):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def should_fail(self):
        o = self.opts
        if o.fail == "none" or self.page != o.page:
            return False
        with Handler.lock:
            Handler.hits += 1
            return o.times == 0 or Handler.hits <= o.times

    def do_GET(self):
        url = urlparse(self.path)
        self.page = parse_qs(url.query).get("page", ["?"])[0]
        if url.path != "/stories" or not self.page.isdigit() or not 1 <= int(self.page) <= LAST_PAGE:
            self.note("404 no such page")
            self.send_json_text(404, json.dumps({"error": "no such page"}))
            return
        self.page = int(self.page)
        answer = {
            "total": TOTAL,
            "page": self.page,
            "next": self.page + 1 if self.page < LAST_PAGE else None,
            "items": page_items(self.page),
        }
        if not self.should_fail():
            self.note("200 healthy, %d items" % len(answer["items"]))
            self.send_json_text(200, json.dumps(answer))
            return

        mode = self.opts.fail
        if mode == "timeout":
            self.note("INJECTED timeout: no answer for %s seconds" % self.opts.hang)
            time.sleep(self.opts.hang)
            try:
                self.send_json_text(200, json.dumps(answer))
            except OSError:
                pass  # the caller gave up and closed the connection
        elif mode == "partial":
            answer["next"] = None
            self.note("INJECTED partial response: 200, says this is the last page")
            self.send_json_text(200, json.dumps(answer))
        elif mode == "rate-limit":
            self.note("INJECTED rate limit: 429, Retry-After %s" % self.opts.retry_after)
            self.send_json_text(429, json.dumps({"error": "too many requests"}),
                                [("Retry-After", str(self.opts.retry_after))])
        elif mode == "malformed":
            text = json.dumps(answer)
            self.note("INJECTED malformed answer: 200, body cut off part-way")
            self.send_json_text(200, text[: len(text) // 2])
        elif mode == "malformed-item":
            del answer["items"][6]["id"]
            self.note("INJECTED malformed item: 200, item 7 on the page has no id")
            self.send_json_text(200, json.dumps(answer))


def main():
    p = argparse.ArgumentParser(description="Fake story service that fails on request.")
    p.add_argument("--port", type=int, default=8799)
    p.add_argument("--fail", choices=MODES, default="none")
    p.add_argument("--page", type=int, default=3)
    p.add_argument("--times", type=int, default=0)
    p.add_argument("--hang", type=float, default=5.0)
    p.add_argument("--retry-after", default="1")
    Handler.opts = p.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", Handler.opts.port), Handler)
    server.daemon_threads = True
    print("service: listening on 127.0.0.1:%d, fail=%s page=%d times=%d"
          % (Handler.opts.port, Handler.opts.fail, Handler.opts.page, Handler.opts.times), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
