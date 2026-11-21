#!/usr/bin/env python3
"""Says whether Trello accepts the key and token in the environment. Reads only. Prints no secret.

It asks Trello one question, "which member is this?", two ways:

    in a header   the way the readers in this repository send the key and token
    in the address the way Trello's own documentation shows first

and prints, for each, the status and Trello's short reason. It also says
whether the key in the environment is the text now on the clipboard, so that
it can be compared with a key just copied from Trello's page without either
being shown.

Nothing here is written to a file. The address that carries the key and token
exists only in memory and is never printed. If a request fails, only the kind
of failure is printed.

    python3 check_trello_credentials.py
"""
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request

KEY, TOKEN = os.environ.get("TRELLO_API_KEY", ""), os.environ.get("TRELLO_API_TOKEN", "")
KNOWN = ("invalid key", "invalid token", "invalid app token", "expired token", "unauthorized", "invalid app key")


def ask(in_header):
    url = "https://api.trello.com/1/members/me?fields=id"
    request = urllib.request.Request(url if in_header else url + "&" + urllib.parse.urlencode({"key": KEY, "token": TOKEN}), method="GET")
    if in_header:
        request.add_header("Authorization", 'OAuth oauth_consumer_key="%s", oauth_token="%s"' % (KEY, TOKEN))
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return "status %d, accepted" % response.status
    except urllib.error.HTTPError as err:
        said = err.read(200).decode("utf-8", "replace").strip().lower()
        reason = next((phrase for phrase in KNOWN if phrase in said), "a reason this script does not know")
        return "status %d, Trello said: %s" % (err.code, reason)
    except Exception as err:  # the address is not printed, only the kind of failure
        return "no answer (%s)" % type(err).__name__


def main():
    print("Key in this terminal:   %d characters, shaped like a Trello key: %s" % (len(KEY), bool(re.fullmatch(r"[0-9a-f]{32}", KEY))))
    print("Token in this terminal: %d characters, starts with ATTA: %s" % (len(TOKEN), TOKEN.startswith("ATTA")))
    try:
        clip = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=5).stdout.strip()
        if re.fullmatch(r"[0-9a-f]{32}", clip):
            print("The clipboard holds something shaped like a key. It is %s the key in this terminal."
                  % ("THE SAME AS" if clip == KEY else "DIFFERENT FROM"))
        else:
            print("The clipboard does not hold something shaped like a key, so no comparison was made.")
    except Exception:
        print("The clipboard could not be read, so no comparison was made.")
    print("Asked of Trello, key and token in a header:      %s" % ask(True))
    print("Asked of Trello, key and token in the address:   %s" % ask(False))


if __name__ == "__main__":
    main()
