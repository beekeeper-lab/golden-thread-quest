#!/usr/bin/env python3
"""Story sync for the base-camp-failure-lab quest.

Reads every page of stories from the fake service (fake_service.py) and saves
them to one local JSON file. The rules it follows are in
participant/context/failure-policy.md.

It only talks to this machine: a URL whose host is not 127.0.0.1 is refused
before any request is sent.

What it saves:

  OUT                    only when every story the service counted was read.
                         The file says "status": "complete".
  OUT.INCOMPLETE.json    when the run failed or skipped something. The file
                         says "status": "incomplete" and why. OUT is not
                         written.
  OUT.EARLIER.json       when the run failed or skipped something and a file
                         from an earlier run was already at OUT. That file
                         is renamed to this, contents unchanged, so that no
                         file named OUT is left after a failure.

The last line of the report is always one of:

  RESULT: COMPLETE ...     exit code 0
  RESULT: INCOMPLETE ...   exit code 2
  RESULT: FAILED ...       exit code 1

Usage: sync.py --out OUT.json [--url http://127.0.0.1:8799]
"""
import argparse
import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse

TIMEOUT_SECONDS = 2
MAX_TRIES = 3  # the first try and 2 retries
MAX_WAIT_SECONDS = 10  # longest single rate-limit wait
MAX_WAITS = 3  # rate-limit waits for one request


class Stop(Exception):
    """The run cannot go on. The message is the reason for the report."""


def say(text):
    print("sync: " + text, flush=True)


def is_timeout(err):
    if isinstance(err, socket.timeout):
        return True
    return isinstance(err, urllib.error.URLError) and isinstance(err.reason, socket.timeout)


def fetch_page(base_url, page):
    """Ask for one page. Return its answer as a dict, or raise Stop."""
    url = "%s/stories?page=%d" % (base_url, page)
    tries = 0   # counts timeouts (policy 1)
    waits = []  # seconds waited for a rate limit (policy 3)
    while True:
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
                body = response.read()
            break
        except urllib.error.HTTPError as err:
            if err.code != 429:
                raise Stop("not handled yet: page %d: status %d" % (page, err.code))
            # Policy 3. Wait as long as the service says, within our limits.
            asked = err.headers.get("Retry-After")
            say("page %d: status 429 (rate limit), service says Retry-After: %s" % (page, asked))
            if asked is None or not asked.isascii() or not asked.isdigit():
                raise Stop("rate limit with no usable wait: page %d" % page)
            seconds = int(asked)
            if seconds > MAX_WAIT_SECONDS:
                raise Stop("rate limit: page %d: service asked for a %d second wait, limit is %d"
                           % (page, seconds, MAX_WAIT_SECONDS))
            if len(waits) == MAX_WAITS:
                raise Stop("rate limit: page %d: still limited after %d waits, service asked for %d more seconds"
                           % (page, MAX_WAITS, seconds))
            say("page %d: wait %d of %d: waiting %d seconds" % (page, len(waits) + 1, MAX_WAITS, seconds))
            started = time.monotonic()
            time.sleep(seconds)
            waits.append(seconds)
            say("page %d: waited %.1f seconds, asking again" % (page, time.monotonic() - started))
        except Exception as err:
            if not is_timeout(err):  # the other failures get their own handling later
                raise Stop("not handled yet: page %d: %s" % (page, err))
            # Policy 1. A read changes nothing, so it is safe to ask again.
            tries += 1
            say("page %d: try %d of %d: no answer within %d seconds (timeout)"
                % (page, tries, MAX_TRIES, TIMEOUT_SECONDS))
            if tries == MAX_TRIES:
                raise Stop("timeout: page %d gave no answer in %d tries" % (page, MAX_TRIES))
            say("page %d: retrying" % page)
    if tries:
        say("page %d: answered on try %d of %d" % (page, tries + 1, MAX_TRIES))
    if waits:
        say("page %d: answered after %d wait(s) of %s seconds"
            % (page, len(waits), ", ".join(str(w) for w in waits)))
    # Policy 4, the whole answer. No repair is tried.
    try:
        answer = json.loads(body)
    except ValueError as err:
        raise Stop("malformed answer: page %d: not JSON: %s" % (page, err))
    if not isinstance(answer, dict) or not isinstance(answer.get("items"), list):
        raise Stop("malformed answer: page %d: no items list" % page)
    nxt = answer.get("next", "absent")
    if nxt is not None and (isinstance(nxt, bool) or not isinstance(nxt, int) or nxt <= page):
        raise Stop("malformed answer: page %d: next page is not a later page number or null" % page)
    return answer


def item_problem(item, seen_ids):
    """Policy 4, one item. Return why it is rejected, or None if it is good."""
    if not isinstance(item, dict):
        return "not an object"
    if "id" not in item:
        return "no id"
    if not isinstance(item["id"], str) or not item["id"].strip():
        return "id is not text"
    if not isinstance(item.get("title"), str):
        return "title is not text"
    if item["id"] in seen_ids:
        return "id already seen in this run"
    return None


def write_json(path, data):
    """Write the whole file or nothing: write beside it, then rename."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
        f.write("\n")
    os.replace(tmp, path)


def run(base_url, out_path):
    items = []     # good items, to be saved
    rejected = []  # one entry per skipped item
    received = 0   # good and rejected together: what the service sent
    total = None
    failure = None
    page = 1
    try:
        while page is not None:
            answer = fetch_page(base_url, page)
            # Policy 2. Without the service's own count there is nothing to
            # check the items against, so the answer is not assumed whole.
            count = answer.get("total")
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise Stop("no count to check against: page %d has no usable total" % page)
            if total is not None and count != total:
                raise Stop("no count to check against: total was %d, page %d says %d" % (total, page, count))
            total = count
            seen = {item["id"] for item in items}
            for position, item in enumerate(answer["items"], 1):
                received += 1
                problem = item_problem(item, seen)
                if problem:
                    # Skip it and go on. The content is not echoed and no fix is guessed.
                    rejected.append({"page": page, "position": position, "reason": problem})
                    say("page %d: rejected item %d on the page: %s (skipped, not repaired)"
                        % (page, position, problem))
                else:
                    items.append({"id": item["id"], "title": item["title"]})
                    seen.add(item["id"])
            say("page %d: read %d items, %d received so far, service says total is %s"
                % (page, len(answer["items"]), received, total))
            page = answer["next"]
        # The service said there are no more pages. Believe its count, not that.
        if received != total:
            raise Stop("partial response: received %d of %s" % (received, total))
    except Stop as stop:
        failure = str(stop)

    incomplete_path = out_path + ".INCOMPLETE.json"
    if failure is None and not rejected:
        write_json(out_path, {"status": "complete", "total": total, "items": items})
        if os.path.exists(incomplete_path):
            os.remove(incomplete_path)  # left by an earlier failed run
        say("RESULT: COMPLETE %d of %d saved to %s" % (len(items), total, out_path))
        return 0
    reason = failure or "%d item(s) rejected" % len(rejected)
    write_json(incomplete_path, {"status": "incomplete", "reason": reason, "service_total": total,
                                 "rejected": rejected, "items": items})
    say("nothing written to %s" % out_path)
    if os.path.exists(out_path):
        # A complete file from an earlier run would read as this run's result.
        # Its contents are kept, under a name that says what it is.
        earlier_path = out_path + ".EARLIER.json"
        os.replace(out_path, earlier_path)
        say("an earlier run's file was at %s: renamed to %s, contents unchanged" % (out_path, earlier_path))
    if failure is None:
        say("RESULT: INCOMPLETE %d of %d saved, %d rejected, kept in %s"
            % (len(items), total, len(rejected), incomplete_path))
        return 2
    say("items read before the failure: %d good, %d rejected (kept in %s, marked incomplete)"
        % (len(items), len(rejected), incomplete_path))
    say("RESULT: FAILED %s" % failure)
    return 1


def main():
    p = argparse.ArgumentParser(description="Read all stories from the fake service.")
    p.add_argument("--url", default="http://127.0.0.1:8799")
    p.add_argument("--out", required=True)
    args = p.parse_args()
    if urlparse(args.url).hostname != "127.0.0.1":
        say("RESULT: FAILED refused: this workflow only talks to 127.0.0.1")
        return 1
    return run(args.url.rstrip("/"), args.out)


if __name__ == "__main__":
    sys.exit(main())
