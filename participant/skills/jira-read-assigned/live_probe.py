"""Read-only probe: does live Jira accept the delta filter `updated >= <milliseconds>` and read it as sync.py assumes?

It sends a few searches, asks Jira for the `updated` field only, and prints counts and timestamps.
It prints no keys, titles or ticket text, and writes no file. It looks at any issue you can see,
not only the ones assigned to you, because the filter needs some issue to act on.

Needs JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN in the shell. Run from the repository root:
  python3 participant/skills/jira-read-assigned/live_probe.py
"""
import importlib.util
import sys
import urllib.parse
from pathlib import Path

spec = importlib.util.spec_from_file_location("sync", Path(__file__).resolve().parent / "sync.py")
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)


def updated_times(settings: dict, jql: str) -> list:
    """Return the `updated` timestamps on the first page of a search, or stop and say Jira refused it."""
    params = {"jql": jql, "maxResults": 100, "fields": "updated"}
    page = sync.get_json(settings, f"{sync.SEARCH_PATH}?{urllib.parse.urlencode(params)}")
    return [issue["fields"]["updated"] for issue in page.get("issues", [])]


def main() -> None:
    settings = sync.read_settings()
    print("probe 1: the five most recently updated issues you can see, from the last 365 days")
    recent = updated_times(settings, 'updated >= "-365d" ORDER BY updated DESC')[:5]
    for value in recent:
        print(f"  updated {value}")
    if len(recent) < 3:
        sys.exit("RESULT: inconclusive. Fewer than three issues are visible, so the filter has nothing to act on.")

    pivot = recent[2]
    pivot_ms = sync.jira_time_ms(pivot)
    print(f"\nprobe 2: updated >= {pivot_ms}   (that is {pivot}, the third one above, as milliseconds since 1970)")
    try:
        got = updated_times(settings, f"updated >= {pivot_ms} ORDER BY updated DESC")
    except SystemExit as error:
        sys.exit(f"RESULT: Jira did NOT accept the milliseconds form. It answered: {error}")
    for value in got[:8]:
        print(f"  updated {value}")
    older = [value for value in got if sync.jira_time_ms(value) < pivot_ms - 60_000]
    print(f"  returned {len(got)}; of those, {len(older)} are more than a minute older than the threshold")
    accepted = len(got) >= 3 and not older

    far_future = pivot_ms + 10 * 365 * 24 * 3600 * 1000
    print(f"\nprobe 3: updated >= {far_future}   (ten years after that)")
    future = updated_times(settings, f"updated >= {far_future}")
    print(f"  returned {len(future)}")

    print(f"\nprobe 4: updated >= {pivot_ms + 1}   (one millisecond after the third issue's timestamp)")
    edge = updated_times(settings, f"updated >= {pivot_ms + 1} ORDER BY updated DESC")
    still_there = pivot in edge
    print(f"  returned {len(edge)}; the third issue is {'still' if still_there else 'no longer'} included")
    print("  (still included means Jira compares more coarsely than a millisecond; either way the 5 minute margin covers it)")

    if accepted and not future:
        print("\nRESULT: Jira accepted the milliseconds form and read it as a point in time, as sync.py assumes.")
    else:
        print("\nRESULT: NOT as assumed. Look at the lines above before trusting delta mode on live Jira.")
        sys.exit(1)


if __name__ == "__main__":
    main()
