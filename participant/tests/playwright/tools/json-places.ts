// A small JSON reader that keeps where everything is (the failure-evidence quest). The check
// (failure-evidence-check.ts) needs each string's real value, after escapes such as a or \/, and
// the line it is on; the copy step (copy-failure-bundle.ts) needs each string's exact place in the
// text, so it can rewrite one string without touching the rest. JSON.parse gives neither.
// It reads standard JSON only and throws on anything else, like JSON.parse.

export type JsonString = { kind: "string"; value: string; start: number; end: number };
export type JsonNode =
  | JsonString
  | { kind: "object"; start: number; entries: { key: JsonString; value: JsonNode }[] }
  | { kind: "array"; start: number; items: JsonNode[] }
  | { kind: "other"; start: number; value: number | boolean | null };

export function parseJson(text: string): JsonNode {
  let at = 0;
  const fail = (what: string): never => {
    throw new SyntaxError(`not JSON: ${what} at position ${at}`);
  };
  const space = () => {
    while (at < text.length && " \t\n\r".includes(text[at])) at++;
  };
  const string = (): JsonString => {
    const start = at;
    at++; // the opening quote
    while (at < text.length && text[at] !== '"') {
      if (text[at] === "\\") at++;
      else if (text.charCodeAt(at) < 0x20) fail("a control character in a string");
      at++;
    }
    if (at >= text.length) fail("an unfinished string");
    at++; // the closing quote
    // The escapes are decoded exactly as JSON.parse decodes them.
    return { kind: "string", value: JSON.parse(text.slice(start, at)) as string, start, end: at };
  };
  const value = (): JsonNode => {
    space();
    const start = at;
    const c = text[at];
    if (c === '"') return string();
    if (c === "{") {
      at++;
      const entries: { key: JsonString; value: JsonNode }[] = [];
      space();
      if (text[at] === "}") {
        at++;
        return { kind: "object", start, entries };
      }
      for (;;) {
        space();
        if (text[at] !== '"') fail("a key that isn't a string");
        const key = string();
        space();
        if (text[at++] !== ":") fail("a missing colon");
        entries.push({ key, value: value() });
        space();
        if (text[at] === ",") at++;
        else if (text[at] === "}") {
          at++;
          return { kind: "object", start, entries };
        } else fail("a missing comma or closing brace");
      }
    }
    if (c === "[") {
      at++;
      const items: JsonNode[] = [];
      space();
      if (text[at] === "]") {
        at++;
        return { kind: "array", start, items };
      }
      for (;;) {
        items.push(value());
        space();
        if (text[at] === ",") at++;
        else if (text[at] === "]") {
          at++;
          return { kind: "array", start, items };
        } else fail("a missing comma or closing bracket");
      }
    }
    const literal = /^(?:-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null)/.exec(text.slice(at, at + 400));
    if (!literal) fail("an unexpected character");
    at += literal![0].length;
    return { kind: "other", start, value: JSON.parse(literal![0]) as number | boolean | null };
  };
  const root = value();
  space();
  if (at !== text.length) fail("text after the end");
  return root;
}

// The text as JSON documents with their offsets: the whole text if it is one document, otherwise
// each line that is one (JSON Lines, as Playwright's trace files are). Lines that aren't JSON are
// left out: the caller checks those as plain text.
export function jsonDocuments(text: string): { node: JsonNode; offset: number }[] {
  try {
    return [{ node: parseJson(text), offset: 0 }];
  } catch {
    const documents: { node: JsonNode; offset: number }[] = [];
    let offset = 0;
    for (const line of text.split("\n")) {
      const trimmed = line.endsWith("\r") ? line.slice(0, -1) : line;
      if (trimmed.trim() !== "") {
        try {
          documents.push({ node: parseJson(trimmed), offset });
        } catch {
          // Not JSON.
        }
      }
      offset += line.length + 1;
    }
    return documents;
  }
}

// Every string in a document, keys included.
export function jsonStrings(node: JsonNode): JsonString[] {
  if (node.kind === "string") return [node];
  if (node.kind === "array") return node.items.flatMap(jsonStrings);
  if (node.kind === "object") return node.entries.flatMap(({ key, value }) => [key, ...jsonStrings(value)]);
  return [];
}
