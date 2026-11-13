// project-setup-check: checks that this Playwright project keeps generated output, environment
// files and credentials out of Git.
//
// It checks that:
//   - every kind of file a test run produces (results, traces, screenshots, downloads, reports)
//     and every environment file is ignored by Git, and names the rule that ignores it;
//   - the project's own files (package, lockfile, configuration, tests, demo app, README and the
//     example environment file) are not ignored, so nothing needed is left out by mistake;
//   - Playwright's browsers are kept out of Git;
//   - no environment file, installed package or downloaded browser anywhere in the repository, and
//     no output from this project's runs, is among the files Git would commit, even one added on
//     purpose;
//   - no credential is found in any file Git would commit, in the staged copy of any tracked file
//     (which is what a commit takes), or in the text of any link (which is what Git commits for a
//     link), using the repository's own secret scanner (tools/secret_scan.py). The quest app's
//     hand-in check is a separate scan with its own rules (for example, it ignores the scanner's
//     "allow" marker), so passing here doesn't guarantee passing that check.
//
// It runs Git and the scanner and only reads; it changes nothing. "Files Git would commit" means
// every tracked file plus every new file that isn't ignored.
//
// Run from this folder (participant/tests/playwright):
//   npm run check-setup
// or from anywhere inside the repository:
//   node participant/tests/playwright/tools/project-setup-check.ts
// It needs Git, and the repository's Python environment (.venv) for the scanner.
// Exit status: 0 passed, 1 failed, 2 Git or the scanner couldn't be run.

import { spawnSync } from "node:child_process";
import { existsSync, lstatSync, mkdirSync, mkdtempSync, readlinkSync, realpathSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const VERSION = "1.0.0";

// Example paths for every kind of file a run produces, relative to this project. Git is asked
// whether each would be ignored; the files don't need to exist.
const MUST_BE_IGNORED: { path: string; what: string }[] = [
  { path: "node_modules/@playwright/test/package.json", what: "installed packages" },
  { path: "test-results/smoke-chromium/trace.zip", what: "a trace" },
  { path: "test-results/smoke-chromium/test-failed-1.png", what: "a failure screenshot" },
  { path: "test-results/smoke-chromium/downloads/ticket.pdf", what: "a file downloaded during a test" },
  { path: "playwright-report/index.html", what: "the HTML report" },
  { path: "blob-report/report.zip", what: "a merged-report blob" },
  { path: "playwright/.cache/component.js", what: "Playwright's build cache" },
  { path: ".env", what: "an environment file" },
  { path: ".env.local", what: "a local environment file" },
  { path: ".env-local", what: "an environment file named with a dash" },
  { path: ".env_production", what: "an environment file named with an underscore" },
    { path: "production.env", what: "an environment file ending in .env" },
  { path: "demo-app/data/orders.json.lock", what: "the demo app's lock on its orders file" },
  { path: "demo-app/data/orders.json.4242.tmp", what: "a half-written orders file" },
];

// The project's own files, which must be committed.
const MUST_NOT_BE_IGNORED: string[] = [
  "package.json",
  "package-lock.json",
  "playwright.config.ts",
  "README.md",
  "tests/smoke.spec.ts",
  "first-independent-test.spec.ts",
  "model-usage.spec.ts",
  "brittle.spec.ts",
  "stable.spec.ts",
  "coupled.spec.ts",
  "isolated.spec.ts",
  "cleanup-proof.spec.ts",
  "api-assisted.spec.ts",
  "ui-only.spec.ts",
  "tagged.spec.ts",
  "support/global-setup.ts",
  "support/global-teardown.ts",
  "support/orders-fixture.ts",
  "pages/example-page.ts",
  "pages/models.ts",
  "demo-app/index.html",
  "demo-app/review.html",
  "demo-app/server.js",
  "demo-app/orders.html",
  "demo-app/data/orders.json",
  "demo-app-redesigned/index.html",
  "demo-app-redesigned/review.html",
  "demo-app-redesigned/server.js",
  "tools/project-setup-check.ts",
  "tools/locator-count.ts",
  "tools/run-in-order.ts",
  "tools/data-isolation-check.ts",
  "tools/break-cancel.ts",
  "tools/tagging-check.ts",
  "tools/select.ts",
  ".gitignore",
  ".env.example",
];

class CannotRun extends Error {}

// A path's real location, following links (on macOS, /var is a link to /private/var), so it can be
// compared with the repository's. The folder may not exist yet, so the nearest existing folder
// above it is resolved and the rest added back.
function realLocation(path: string): string {
  const full = resolve(path);
  if (existsSync(full)) return realpathSync(full);
  const parent = dirname(full);
  return parent === full ? full : join(realLocation(parent), basename(full));
}

function run(command: string, args: string[], cwd: string): { status: number; stdout: string; stderr: string } {
  const result = spawnSync(command, args, { cwd, encoding: "utf8" });
  if (result.error) throw new CannotRun(`couldn't run ${command}: ${result.error.message}`);
  return { status: result.status ?? 1, stdout: result.stdout ?? "", stderr: result.stderr ?? "" };
}

// Runs a Git command and stops the check ("couldn't run", exit 2) if Git answers with anything other
// than an expected status, so a failing Git command can never be read as "nothing found". Most
// commands must succeed (0); "git check-ignore" answers 0 for ignored and 1 for not ignored.
function git(args: string[], root: string, expected: number[] = [0]): { status: number; stdout: string; stderr: string } {
  const result = run("git", args, root);
  if (!expected.includes(result.status)) {
    throw new CannotRun(`"git ${args.slice(0, 2).join(" ")}" failed (exit ${result.status}): ${result.stderr.trim()}`);
  }
  return result;
}

// Runs the repository's scanner over the given files on disk and over the staged copy of every
// tracked file, because a commit takes the staged copy, which can differ from the file on disk or
// be hidden from it (a file marked skip-worktree or assume-unchanged, or a sparse checkout). Each
// staged copy is read exactly as Git stores it, with no conversion: a file that Git writes to disk
// in another encoding or through a filter is still scanned as it would be committed, and a link is
// scanned as the text of where it points, which is what Git stores for it. The text of each link on
// disk is written out as well, since that text is what a new link would commit. The copies go into
// two temporary folders that are removed before returning; their paths are returned so findings in
// them can be reported as "staged copy of ..." and "link text of ...".
function scanWithStagedCopies(
  root: string,
  python: string,
  scanner: string,
  files: string[],
): { scan: ReturnType<typeof spawnSync>; staging: string; linkTexts: string; stagedCopies: string[] } {
  const staging = mkdtempSync(join(tmpdir(), "project-setup-check-"));
  const linkTexts = mkdtempSync(join(tmpdir(), "project-setup-check-links-"));
  const writeCopy = (copy: string, contents: string | Buffer): void => {
    mkdirSync(dirname(copy), { recursive: true });
    writeFileSync(copy, contents);
  };
  try {
    // "git ls-files -s" lists "<mode> <object> <stage>\t<path>" for every staged file. Submodules
    // (mode 160000) have no contents of their own here and are left out.
    const entries = git(["ls-files", "--stage", "-z"], root)
      .stdout.split("\0")
      .filter((entry) => entry !== "")
      .map((entry) => {
        const tab = entry.indexOf("\t");
        const [mode = "", object = "", stage = "0"] = entry.slice(0, tab).split(" ");
        return { mode, object, stage, path: entry.slice(tab + 1) };
      })
      .filter((entry) => entry.mode !== "160000");
    // "git cat-file --batch" prints "<object> blob <size>\n<contents>\n" for each object it's given.
    const batch = spawnSync("git", ["cat-file", "--batch"], {
      cwd: root,
      input: entries.map((entry) => `${entry.object}\n`).join(""),
      maxBuffer: 1024 * 1024 * 1024,
    });
    if (batch.error || batch.status !== 0) {
      throw new CannotRun(`Git couldn't read the staged files: ${batch.error?.message ?? String(batch.stderr).trim()}`);
    }
    const stagedCopies: string[] = [];
    let at = 0;
    for (const entry of entries) {
      const lineEnd = batch.stdout.indexOf(10, at);
      const [, type, size] = batch.stdout.subarray(at, lineEnd).toString("utf8").split(" ");
      if (lineEnd < 0 || type !== "blob" || size === undefined) {
        throw new CannotRun(`Git couldn't read the staged copy of ${entry.path}`);
      }
      const contents = batch.stdout.subarray(lineEnd + 1, lineEnd + 1 + Number(size));
      at = lineEnd + 1 + Number(size) + 1;
      // During an unfinished merge Git keeps up to three versions of a file (stages 1 to 3); each
      // gets its own place so none overwrites another.
      const copy =
        entry.stage === "0" ? join(staging, entry.path) : join(staging, `merge-stage-${entry.stage}`, entry.path);
      writeCopy(copy, contents);
      stagedCopies.push(copy);
    }
    const linkCopies: string[] = [];
    for (const file of files) {
      const onDisk = join(root, file);
      let isLink = false;
      try {
        isLink = lstatSync(onDisk).isSymbolicLink();
      } catch {
        continue;
      }
      if (!isLink) continue;
      const copy = join(linkTexts, file);
      writeCopy(copy, readlinkSync(onDisk));
      linkCopies.push(copy);
    }
    // "--" marks the end of the scanner's options, so a file named like an option ("--json") is
    // scanned as a file instead of changing how the scanner runs.
    const scan = spawnSync(python, [scanner, "--", ...files, ...stagedCopies, ...linkCopies], {
      cwd: root,
      encoding: "utf8",
      maxBuffer: 16 * 1024 * 1024,
    });
    return { scan, staging, linkTexts, stagedCopies };
  } finally {
    rmSync(staging, { recursive: true, force: true });
    rmSync(linkTexts, { recursive: true, force: true });
  }
}

// Whether Git ignores a path because of a rule in one of the repository's own .gitignore files,
// which every copy of the repository has. "--no-index" asks about the path itself, whether or not a
// file is there. A rule that exists only on this computer (.git/info/exclude, or a personal ignore
// file set with core.excludesFile) doesn't count, since a teammate's copy wouldn't have it. The plain
// question decides whether the path is ignored; "-v" then names the deciding rule and its file.
// ("-v" alone can't decide: it also reports a rule that un-ignores the path, such as "!.env.local".)
function ignoredByRepository(root: string, path: string): { ignored: boolean; rule: string } {
  if (git(["check-ignore", "--no-index", "-q", path], root, [0, 1]).status !== 0) return { ignored: false, rule: "" };
  const rule = git(["check-ignore", "--no-index", "-v", path], root).stdout.split("\t")[0] ?? "";
  const source = /^(.*?):\d+:/.exec(rule)?.[1] ?? "";
  // A personal ignore file is often named ".gitignore" too (such as ~/.gitignore), so the rule's file
  // must also be inside the repository: Git names those files by a path relative to the top folder.
  const fromRepository = basename(source) === ".gitignore" && !isAbsolute(source) && !source.startsWith("..");
  return { ignored: fromRepository, rule };
}

function main(): number {
  const project = resolve(dirname(fileURLToPath(import.meta.url)), "..");
  const top = run("git", ["rev-parse", "--show-toplevel"], project);
  if (top.status !== 0) throw new CannotRun("this folder isn't inside a Git repository");
  const root = top.stdout.trim();
  const projectPath = relative(root, project);

  const out: string[] = [];
  const check = (passed: boolean, text: string, details: string[] = []): void => {
    out.push(`${passed ? "PASS" : "FAIL"}  ${text}`);
    for (const line of details) out.push(`      ${line}`);
  };
  out.push(`project-setup-check ${VERSION}`);
  out.push(`project: ${projectPath}`);

  // Generated output and environment files are ignored by the repository's own .gitignore files.
  const ignored: string[] = [];
  const notIgnored: string[] = [];
  for (const { path, what } of MUST_BE_IGNORED) {
    const full = join(projectPath, path);
    const answer = ignoredByRepository(root, full);
    if (answer.ignored) {
      ignored.push(`${what}: ${full} (rule ${answer.rule})`);
    } else if (answer.rule !== "") {
      notIgnored.push(`${what}: ${full} is ignored only on this computer (rule ${answer.rule}), not by a .gitignore file`);
    } else {
      notIgnored.push(`${what}: ${full} is NOT ignored`);
    }
  }
  check(
    notIgnored.length === 0,
    `generated output and environment files are ignored by Git (${ignored.length} of ${MUST_BE_IGNORED.length})`,
    [...notIgnored, ...ignored],
  );

  // The project's own files are not ignored.
  const wronglyIgnored = MUST_NOT_BE_IGNORED.filter(
    (path) => git(["check-ignore", "--no-index", "-q", join(projectPath, path)], root, [0, 1]).status === 0,
  );
  check(
    wronglyIgnored.length === 0,
    `the project's own files are not ignored (${MUST_NOT_BE_IGNORED.length - wronglyIgnored.length} of ${MUST_NOT_BE_IGNORED.length})`,
    wronglyIgnored.map((path) => `${join(projectPath, path)} is ignored, so it would be left out`),
  );

  // Browsers are kept out of Git: in Playwright's own cache folder outside the repository (the
  // default), in node_modules when PLAYWRIGHT_BROWSERS_PATH is "0", or in the folder that variable
  // names, which must be outside the repository or ignored by Git.
  const browsers = process.env.PLAYWRIGHT_BROWSERS_PATH;
  // Where browsers go inside the repository, if they do (relative to it), for the commit check below.
  let browsersInRepo: string | null = null;
  let browserPlace: string;
  let browsersOk: boolean;
  if (browsers === undefined || browsers === "") {
    browserPlace = "Playwright's own cache folder, outside the repository";
    browsersOk = true;
  } else if (browsers === "0") {
    browserPlace = "node_modules, which is ignored";
    browsersOk = ignoredByRepository(root, join(projectPath, "node_modules/x")).ignored;
  } else {
    const inside = relative(realLocation(root), realLocation(browsers));
    // Only a real step up ("..", or ".." followed by a separator) leaves the repository; the
    // repository's own top folder (an empty relative path) and a name like "..cache" are inside.
    const isInside = !(inside === ".." || inside.startsWith(`..${sep}`) || isAbsolute(inside));
    if (isInside) browsersInRepo = inside;
    browserPlace = !isInside
      ? "a folder outside the repository"
      : inside === ""
        ? "the repository's own top folder"
        : `${inside}, inside the repository`;
    browsersOk = !isInside || ignoredByRepository(root, join(inside, "x")).ignored;
  }
  check(
    browsersOk,
    `downloaded browsers are kept out of Git (${browserPlace})`,
    browsersOk ? [] : ["PLAYWRIGHT_BROWSERS_PATH puts the browsers inside the repository where Git would commit them"],
  );

  // The files Git would commit: everything tracked, plus new files that aren't ignored.
  const listed = git(["ls-files", "--cached", "--others", "--exclude-standard", "-z"], root);
  const files = listed.stdout.split("\0").filter((file) => file !== "");

  // No environment file would be committed anywhere in the repository (the example file is
  // allowed). Environment files go by several names: ".env" and ".env.local", ".env-local" or
  // ".env_production", ".envrc" (read by direnv) and "production.env", in any letter case.
  const envFile = /(^|\/)(\.env([._-][^/]*)?|\.envrc|[^/]+\.env)$/i;
  const envFiles = files.filter((file) => envFile.test(file) && !/(^|\/)\.env\.example$/i.test(file));
  check(
    envFiles.length === 0,
    `no environment file is among the ${files.length} files Git would commit`,
    envFiles.map((file) => `${file} would be committed`),
  );

  // Nothing this project's runs produce, no installed package and no downloaded browser is among the
  // files Git would commit, even if it was added to Git on purpose before an ignore rule existed.
  // (The ignore checks above only ask about example paths; this looks at what is actually there.)
  // Installed packages are recognised in a node_modules folder anywhere in the repository; the
  // other output folders only in this project, since names such as "test-results" aren't
  // Playwright's alone.
  const generated = ["node_modules", "test-results", "playwright-report", "blob-report", "playwright/.cache"].map(
    (folder) => `${projectPath}/${folder}/`,
  );
  if (browsersInRepo !== null && browsersInRepo !== "") generated.push(`${browsersInRepo}/`);
  // Downloaded browsers are also recognised by the folder names Playwright gives them, wherever they
  // are, so a download made earlier with a different PLAYWRIGHT_BROWSERS_PATH is caught even when
  // that setting isn't set now. Playwright names each folder after a browser it has ever offered,
  // with "_" for "-", then its revision ("chromium-1243", "chromium_headless_shell-1243",
  // "firefox_beta-1234"); the folder holding them is ".local-browsers" or "ms-playwright".
  const browserFolder =
    /(^|\/)(android|chromium|chromium_headless_shell|chromium_tip_of_tree|chromium_tip_of_tree_headless_shell|firefox|firefox_beta|webkit|ffmpeg|winldd)-\d+\/|(^|\/)(\.local-browsers|ms-playwright)\//;
    const installedPackage = /(^|\/)node_modules\//i;
  // The demo app's lock (a committed one would stop the app starting in a fresh clone) and its
  // half-written orders files.
  const ordersWorkFile = (file: string) =>
    file === `${projectPath}/demo-app/data/orders.json.lock` ||
    (file.startsWith(`${projectPath}/demo-app/data/`) && file.endsWith(".tmp"));
  const committedGenerated = files.filter(
    (file) =>
      generated.some((folder) => file.startsWith(folder)) ||
      installedPackage.test(file) ||
      browserFolder.test(file) ||
      ordersWorkFile(file),
  );
  check(
    committedGenerated.length === 0,
        "no output from this project's runs, orders lock or half-written orders file, installed package or downloaded browser is among the files Git would commit",
    committedGenerated.slice(0, 20).map((file) => `${file} would be committed`),
  );

  // No credential in any file Git would commit, by the repository's own scanner. It prints
  // "path:line:column: [pattern] description" for each finding, never the secret itself.
  const python = join(root, ".venv", "bin", "python");
  const scanner = join(root, "tools", "secret_scan.py");
  if (!existsSync(python) || !existsSync(scanner)) {
    throw new CannotRun("the repository's secret scanner (.venv and tools/secret_scan.py) isn't set up");
  }
  // A commit takes the staged copy of a file, which can differ from the copy on disk (a token staged
  // and then deleted from the file on disk would still be committed), so every staged copy is
  // scanned as well, exactly as Git stores it, and so is the text of every link, which is what Git
  // commits for a link.
  const { scan, staging, linkTexts, stagedCopies } = scanWithStagedCopies(root, python, scanner, files);
  if (scan.error) throw new CannotRun(`couldn't run the secret scanner: ${scan.error.message}`);
  const scanLines = `${scan.stdout ?? ""}${scan.stderr ?? ""}`
    .trim()
    .split("\n")
    .filter((line) => line !== "")
    .map((line) => line.replace(`${staging}${sep}`, "staged copy of ").replace(`${linkTexts}${sep}`, "link text of "));
  const summary = scanLines.find((line) => line.startsWith("secret-scan:")) ?? "";
  // The scanner exits 0 (nothing found) or 1 (findings), always with a summary line. Anything else
  // means it didn't finish, so nothing was scanned: that is "couldn't check", not a failed check.
  if (summary === "" || (scan.status !== 0 && scan.status !== 1)) {
    throw new CannotRun(`the secret scanner didn't finish (exit ${scan.status ?? "none"}): ${scanLines.slice(-3).join(" ")}`);
  }
  const clean = scan.status === 0 && /, 0 finding\(s\)$/.test(summary);
  check(
    clean,
    `no credential found in the files Git would commit (${summary.replace("secret-scan: ", "") || "no summary from the scanner"}` +
      `${stagedCopies.length > 0 ? `, including the staged copies of all ${stagedCopies.length} tracked files` : ""})`,
    clean ? [] : scanLines.filter((line) => !line.startsWith("secret-scan:")),
  );

  const failed = out.some((line) => line.startsWith("FAIL"));
  out.push(failed ? "RESULT: FAILED" : "RESULT: PASSED");
  console.log(out.join("\n"));
  return failed ? 1 : 0;
}

try {
  process.exitCode = main();
} catch (error) {
  // Anything that stops the check from running is reported as "couldn't check" (2), never as an
  // ordinary FAIL (1).
  const message = error instanceof Error ? error.message : String(error);
  console.error(`project-setup-check ${VERSION}: ${error instanceof CannotRun ? message : `stopped unexpectedly: ${message}`}`);
  process.exitCode = 2;
}
