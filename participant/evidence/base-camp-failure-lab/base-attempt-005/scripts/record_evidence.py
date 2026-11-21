#!/usr/bin/env python3
"""Records logs/failure-runs.txt for the base-camp-failure-lab quest.

For each case it starts the fake service with one failure switched on, runs
sync.py against it, stops the service, and writes what both of them printed
into the log, in the order it was printed. Lines from the service start with
"service:" and lines from the workflow start with "sync:".

Each run saves into work/<case>.json or work/<case>.json.INCOMPLETE.json.
The work folder is emptied first, so the files there come from this recording.

Run from the attempt folder:  python3 scripts/record_evidence.py
"""
import os
import socket
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
PORT = 8799

# (case name, policy section, what the case shows, list of service options).
# A case with two sets of options is two runs, one after the other, saving to
# the same output name.
CASES = [
    ("0-healthy", "control", "no failure switched on", [["--fail", "none"]]),
    ("1a-timeout-lasting", "1. Timeout", "page 3 never answers", [["--fail", "timeout"]]),
    ("1b-timeout-recovers", "1. Timeout", "page 3 answers on the third try", [["--fail", "timeout", "--times", "2"]]),
    ("2-partial", "2. Partial response", "page 3 says it is the last page", [["--fail", "partial"]]),
    ("3a-rate-limit-recovers", "3. Rate limit", "page 3 refused once, wait of 2 seconds asked",
     [["--fail", "rate-limit", "--times", "1", "--retry-after", "2"]]),
    ("3b-rate-limit-lasting", "3. Rate limit", "page 3 refused every time, wait of 1 second asked",
     [["--fail", "rate-limit", "--retry-after", "1"]]),
    ("3c-rate-limit-too-long", "3. Rate limit", "page 3 refused, wait of 60 seconds asked",
     [["--fail", "rate-limit", "--retry-after", "60"]]),
    ("4a-malformed-answer", "4. Malformed data", "page 3's answer is cut off part-way", [["--fail", "malformed"]]),
    ("4b-malformed-item", "4. Malformed data", "one item on page 3 has no id", [["--fail", "malformed-item"]]),
    ("5-failure-after-earlier-success", "5. After any failure",
     "a healthy run, then a partial response saving to the same name",
     [["--fail", "none"], ["--fail", "partial"]]),
]


def wait_until_listening():
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", PORT), timeout=0.2).close()
            return
        except OSError:
            time.sleep(0.1)
    sys.exit("the fake service did not start")


def main():
    os.chdir(ATTEMPT)
    os.makedirs("work", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    for name in os.listdir("work"):
        os.remove(os.path.join("work", name))
    path = os.path.join("logs", "failure-runs.txt")
    with open(path, "w", encoding="utf-8") as log:
        def write(text=""):
            log.write(text + "\n")
            log.flush()

        write("Failure runs for base-camp-failure-lab, attempt base-attempt-005")
        write("Recorded by scripts/record_evidence.py on %s" % time.strftime("%Y-%m-%d", time.gmtime()))
        write("")
        write("Every run is sync.py reading from fake_service.py on 127.0.0.1:%d. No real service" % PORT)
        write("is contacted. The stories are made up (STORY-001 to STORY-100), so nothing here")
        write("needed redacting. A line with INJECTED is the service failing on purpose.")
        write("The policy the workflow follows is participant/context/failure-policy.md.")
        for name, section, shows, steps in CASES:
            write("")
            write("=" * 78)
            write("RUN %s   (policy %s: %s)" % (name, section, shows))
            for options in steps:
                write("$ fake_service.py %s" % " ".join(options))
                write("$ sync.py --out work/%s.json" % name)
                write("-" * 78)
                service = subprocess.Popen(
                    [sys.executable, "-u", os.path.join("scripts", "fake_service.py"), "--port", str(PORT)] + options,
                    stdout=log, stderr=subprocess.STDOUT)
                try:
                    wait_until_listening()
                    done = subprocess.run(
                        [sys.executable, "-u", os.path.join("scripts", "sync.py"), "--out", "work/%s.json" % name],
                        stdout=log, stderr=subprocess.STDOUT)
                finally:
                    service.terminate()
                    service.wait()
                log.seek(0, os.SEEK_END)
                write("-" * 78)
                write("sync.py exit code: %d" % done.returncode)
                print("%-34s exit code %d" % (name, done.returncode))
    print("wrote %s" % path)


if __name__ == "__main__":
    main()
