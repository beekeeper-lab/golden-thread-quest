# Vendored third-party files

## `axe.min.js`

axe-core, used only by `tests/ui/test_browser_flows.py` to run automated accessibility
checks. It is vendored rather than installed because the accessibility suite has to run in
CI and on a developer machine without a Node toolchain or network access, and a check that
silently skips is a check nobody notices has stopped running.

It is never served, never referenced by a generated page, and never loaded by the
application. License: Mozilla Public License 2.0.
