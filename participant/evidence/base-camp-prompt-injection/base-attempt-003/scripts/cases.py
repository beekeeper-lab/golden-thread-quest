"""Read the cases from participant/context/injection-cases.md.

Everything in a case's item is untrusted text. This module only parses it.
"""
import json
import re

ITEM_FIELDS = ("key", "title", "reporter", "description", "comments", "attachments", "tool_results")
BULLETS = (("hides_in", "Hides in"), ("asks_for", "Asks for"), ("expected", "Expected behavior"))


class CaseError(Exception):
    pass


def item_fields(item):
    """Every piece of text in an item, as (field name, text) pairs."""
    out = [("key", item["key"]), ("title", item["title"]), ("reporter", item["reporter"]),
           ("description", item["description"])]
    for i, c in enumerate(item["comments"]):
        out.append((f"comments[{i}].author", c["author"]))
        out.append((f"comments[{i}].body", c["body"]))
    for i, a in enumerate(item["attachments"]):
        out.append((f"attachments[{i}]", a))
    for i, t in enumerate(item["tool_results"]):
        out.append((f"tool_results[{i}].tool", t["tool"]))
        out.append((f"tool_results[{i}].output", t["output"]))
    return out


def _check_item(cid, item):
    if not isinstance(item, dict) or set(item) != set(ITEM_FIELDS):
        raise CaseError(f"case {cid}: item must have exactly these fields: {', '.join(ITEM_FIELDS)}")
    for f in ("key", "title", "reporter", "description"):
        if not isinstance(item[f], str):
            raise CaseError(f"case {cid}: item.{f} must be text")
    for f, keys in (("comments", {"author", "body"}), ("tool_results", {"tool", "output"})):
        if not isinstance(item[f], list):
            raise CaseError(f"case {cid}: item.{f} must be a list")
        for entry in item[f]:
            if not isinstance(entry, dict) or set(entry) != keys or not all(isinstance(v, str) for v in entry.values()):
                raise CaseError(f"case {cid}: each entry in item.{f} needs text for {sorted(keys)}")
    if not isinstance(item["attachments"], list) or not all(isinstance(a, str) for a in item["attachments"]):
        raise CaseError(f"case {cid}: item.attachments must be a list of names")


def load_cases(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    parts = re.split(r"(?m)^## case: *(.+?) *$", text)
    cases, seen = [], set()
    for i in range(1, len(parts), 2):
        cid, body = parts[i], parts[i + 1]
        nxt = re.search(r"(?m)^## ", body)
        if nxt:
            body = body[:nxt.start()]
        if cid in seen:
            raise CaseError(f"case {cid}: this id is used twice")
        seen.add(cid)
        case = {"id": cid}
        for key, label in BULLETS:
            m = re.search(rf"(?m)^- \*\*{re.escape(label)}:\*\* *(.+)$", body)
            if not m or not m.group(1).strip():
                raise CaseError(f"case {cid}: the '{label}' line is missing")
            case[key] = m.group(1).strip()
        blocks = re.findall(r"(?ms)^```json\n(.*?)\n```", body)
        if len(blocks) != 1:
            raise CaseError(f"case {cid}: needs exactly one json block, found {len(blocks)}")
        try:
            data = json.loads(blocks[0])
        except ValueError as e:
            raise CaseError(f"case {cid}: the json block does not parse ({e})")
        if not isinstance(data, dict) or set(data) != {"expect_flag", "harmless", "instruction", "obey_calls", "item"}:
            raise CaseError(f"case {cid}: the json block needs expect_flag, harmless, instruction, obey_calls and item")
        oc = data["obey_calls"]
        if not isinstance(oc, list) or not all(isinstance(o, dict) and isinstance(o.get("tool"), str)
                                               and set(o) <= {"tool", "contains"} and isinstance(o.get("contains", ""), str) for o in oc):
            raise CaseError(f"case {cid}: obey_calls must be a list of entries with a tool and, optionally, contains")
        if data["expect_flag"] and not oc:
            raise CaseError(f"case {cid}: a case with an instruction must say which decoy calls would mean it was obeyed")
        if not isinstance(data["expect_flag"], bool) or not isinstance(data["harmless"], bool):
            raise CaseError(f"case {cid}: expect_flag and harmless must be true or false")
        _check_item(cid, data["item"])
        ins = data["instruction"]
        if data["expect_flag"]:
            if not isinstance(ins, str) or not ins.strip():
                raise CaseError(f"case {cid}: expect_flag is true, so instruction must hold the embedded text")
            if not any(ins in t for _, t in item_fields(data["item"])):
                raise CaseError(f"case {cid}: the instruction is not in the item exactly as written")
        elif ins is not None:
            raise CaseError(f"case {cid}: expect_flag is false, so instruction must be null")
        case.update(data)
        cases.append(case)
    if not cases:
        raise CaseError("no cases found (each starts with a '## case: <id>' heading)")
    return cases
