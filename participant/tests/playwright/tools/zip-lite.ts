// A small zip reader and writer for Playwright's trace.zip (the failure-evidence quest), so the copy
// step (copy-failure-bundle.ts) and the check (failure-evidence-check.ts) can look inside a trace
// without another package or a system tool. It understands what Playwright writes: files stored as
// they are (method 0) or compressed (method 8, "deflate"). Anything else (an encrypted member,
// another compression, a zip over 4 GB, a damaged or ambiguous directory, a wrong checksum, a name in
// an older encoding, headers that disagree) is refused with an error rather than skipped, so a check
// can never quietly miss a member it couldn't read.

import { crc32, deflateRawSync, inflateRawSync } from "node:zlib";

export type ZipEntry = { name: string; data: Buffer };
// Everything a zip holds besides its members' names and contents: the archive's comment, and each
// member's comment and extra fields (Playwright's traces carry a 9-byte timestamp per member). Not
// needed to read a member, but a value could hide there, so the check scans it too.
export type ZipMetadata = { where: string; data: Buffer };

const END_OF_DIRECTORY = 0x06054b50;
const DIRECTORY_ENTRY = 0x02014b50;
const LOCAL_HEADER = 0x04034b50;

export function readZip(zip: Buffer): ZipEntry[] {
  return readZipWithMetadata(zip).entries;
}

export function readZipWithMetadata(zip: Buffer): { entries: ZipEntry[]; metadata: ZipMetadata[] } {
  if (zip.length < 22) throw new Error("not a zip file (too short)");
  // The end-of-directory record is the last thing in the file: 22 bytes plus its comment. Every
  // place that could hold one is checked, and exactly one must fit (its comment ends the file, it
  // describes a single-disk zip, and its directory ends where it starts), so a look-alike record
  // hidden in a comment can't make the reader skip members.
  const fits: number[] = [];
  for (let at = zip.length - 22; at >= Math.max(0, zip.length - 22 - 0xffff); at--) {
    if (zip.readUInt32LE(at) !== END_OF_DIRECTORY) continue;
    const onDisk = zip.readUInt16LE(at + 8);
    const total = zip.readUInt16LE(at + 10);
    const directorySize = zip.readUInt32LE(at + 12);
    const directoryStart = zip.readUInt32LE(at + 16);
    if (
      at + 22 + zip.readUInt16LE(at + 20) === zip.length &&
      zip.readUInt16LE(at + 4) === 0 &&
      zip.readUInt16LE(at + 6) === 0 &&
      onDisk === total &&
      directoryStart + directorySize === at
    ) {
      fits.push(at);
    }
  }
  if (fits.length === 0) throw new Error("not a zip file, or a damaged one (no end-of-directory record that fits)");
  if (fits.length > 1) throw new Error("ambiguous zip (more than one end-of-directory record fits)");
  const end = fits[0];
  const count = zip.readUInt16LE(end + 10);
  const directoryEnd = end;
  let at = zip.readUInt32LE(end + 16);
  if (count === 0xffff || at === 0xffffffff) throw new Error("a zip over 4 GB or with 65,535+ members isn't supported");

  const entries: ZipEntry[] = [];
  const metadata: ZipMetadata[] = [];
  const archiveComment = zip.subarray(end + 22);
  if (archiveComment.length > 0) metadata.push({ where: "the archive's comment", data: archiveComment });
  for (let i = 0; i < count; i++) {
    if (at + 46 > directoryEnd || zip.readUInt32LE(at) !== DIRECTORY_ENTRY) {
      throw new Error(`damaged zip: directory entry ${i + 1} not found`);
    }
    const flags = zip.readUInt16LE(at + 8);
    const method = zip.readUInt16LE(at + 10);
    const checksum = zip.readUInt32LE(at + 16);
    const packedSize = zip.readUInt32LE(at + 20);
    const size = zip.readUInt32LE(at + 24);
    const nameLength = zip.readUInt16LE(at + 28);
    const extraLength = zip.readUInt16LE(at + 30);
    const commentLength = zip.readUInt16LE(at + 32);
    const local = zip.readUInt32LE(at + 42);
    const nameBytes = zip.subarray(at + 46, at + 46 + nameLength);
    // A name marked UTF-8 must be valid UTF-8; an unmarked one (an older encoding) must be plain
    // ASCII, which reads the same in every encoding. Anything else is refused, so a name is never
    // silently changed.
    let name: string;
    if (flags & 0x800) {
      try {
        name = new TextDecoder("utf-8", { fatal: true }).decode(nameBytes);
      } catch {
        throw new Error(`damaged zip: member ${i + 1}'s name isn't valid UTF-8`);
      }
    } else if (nameBytes.every((byte) => byte < 0x80)) name = nameBytes.toString("ascii");
    else throw new Error(`member ${i + 1}'s name uses an older encoding, which isn't supported`);
    const extra = zip.subarray(at + 46 + nameLength, at + 46 + nameLength + extraLength);
    const comment = zip.subarray(at + 46 + nameLength + extraLength, at + 46 + nameLength + extraLength + commentLength);
    if (extra.length > 0) metadata.push({ where: `${name}'s extra fields`, data: extra });
    if (comment.length > 0) metadata.push({ where: `${name}'s comment`, data: comment });
    at += 46 + nameLength + extraLength + commentLength;
    if (at > directoryEnd) throw new Error(`damaged zip: directory entry ${i + 1} runs past the directory`);

    if (flags & 1) throw new Error(`${name}: encrypted members aren't supported`);
    if (packedSize === 0xffffffff || size === 0xffffffff || local === 0xffffffff) {
      throw new Error(`${name}: members over 4 GB aren't supported`);
    }
    if (local + 30 > zip.length || zip.readUInt32LE(local) !== LOCAL_HEADER) throw new Error(`${name}: damaged zip (no local header)`);
    // The local header must agree with the directory on how the member is stored.
    if (zip.readUInt16LE(local + 6) !== flags || zip.readUInt16LE(local + 8) !== method) {
      throw new Error(`${name}: damaged zip (the local header and the directory disagree on how it is stored)`);
    }
    const localNameLength = zip.readUInt16LE(local + 26);
    if (!zip.subarray(local + 30, local + 30 + localNameLength).equals(nameBytes)) {
      throw new Error(`${name}: damaged zip (the local header names another file)`);
    }
    const localExtra = zip.subarray(local + 30 + localNameLength, local + 30 + localNameLength + zip.readUInt16LE(local + 28));
    if (localExtra.length > 0) metadata.push({ where: `${name}'s local extra fields`, data: localExtra });
    const start = local + 30 + localNameLength + localExtra.length;
    if (start + packedSize > zip.length) throw new Error(`${name}: damaged zip (cut short)`);
    const packed = zip.subarray(start, start + packedSize);
    let data: Buffer;
    if (method === 0) data = Buffer.from(packed);
    else if (method === 8) data = inflateRawSync(packed);
    else throw new Error(`${name}: compression method ${method} isn't supported`);
    if (data.length !== size) throw new Error(`${name}: damaged zip (size doesn't match)`);
    if (crc32(data) !== checksum) throw new Error(`${name}: damaged zip (checksum doesn't match)`);
    entries.push({ name, data });
  }
  if (at !== directoryEnd) throw new Error("damaged zip: the directory holds more than its member count says");
  return { entries, metadata };
}

export function writeZip(entries: ZipEntry[]): Buffer {
  const parts: Buffer[] = [];
  const directory: Buffer[] = [];
  let offset = 0;
  for (const { name, data } of entries) {
    const nameBytes = Buffer.from(name, "utf8");
    const packed = deflateRawSync(data);
    const checksum = crc32(data);
    const local = Buffer.alloc(30);
    local.writeUInt32LE(LOCAL_HEADER, 0);
    local.writeUInt16LE(20, 4); // version needed: 2.0
    local.writeUInt16LE(0x0800, 6); // names are UTF-8
    local.writeUInt16LE(8, 8); // deflate
    local.writeUInt32LE(checksum, 14);
    local.writeUInt32LE(packed.length, 18);
    local.writeUInt32LE(data.length, 22);
    local.writeUInt16LE(nameBytes.length, 26);
    const entry = Buffer.alloc(46);
    entry.writeUInt32LE(DIRECTORY_ENTRY, 0);
    entry.writeUInt16LE(20, 4);
    entry.writeUInt16LE(20, 6);
    entry.writeUInt16LE(0x0800, 8);
    entry.writeUInt16LE(8, 10);
    entry.writeUInt32LE(checksum, 16);
    entry.writeUInt32LE(packed.length, 20);
    entry.writeUInt32LE(data.length, 24);
    entry.writeUInt16LE(nameBytes.length, 28);
    entry.writeUInt32LE(offset, 42);
    parts.push(local, nameBytes, packed);
    directory.push(entry, nameBytes);
    offset += local.length + nameBytes.length + packed.length;
    if (offset > 0xffffffff) throw new Error("a zip over 4 GB isn't supported");
  }
  const directoryBytes = Buffer.concat(directory);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(END_OF_DIRECTORY, 0);
  end.writeUInt16LE(entries.length, 8);
  end.writeUInt16LE(entries.length, 10);
  end.writeUInt32LE(directoryBytes.length, 12);
  end.writeUInt32LE(offset, 16);
  return Buffer.concat([...parts, directoryBytes, end]);
}

// A file or member as text, or null if it isn't text (an image, for example). UTF-8 (with or
// without a byte-order mark) and UTF-16 (with a byte-order mark, or without one when every other
// byte is zero, as plain ASCII text in UTF-16 is) are read; the encoding is returned so a changed
// text can be written back the same way.
export type TextEncoding = "utf8" | "utf8-bom" | "utf16le" | "utf16be" | "utf16le-plain" | "utf16be-plain";

export function decodeText(data: Buffer): { text: string; encoding: TextEncoding } | null {
  const strict = (label: string, bytes: Buffer) => new TextDecoder(label, { fatal: true }).decode(bytes);
  try {
    if (data[0] === 0xef && data[1] === 0xbb && data[2] === 0xbf) return { text: strict("utf-8", data.subarray(3)), encoding: "utf8-bom" };
    if (data[0] === 0xff && data[1] === 0xfe) return { text: strict("utf-16le", data.subarray(2)), encoding: "utf16le" };
    if (data[0] === 0xfe && data[1] === 0xff) return { text: strict("utf-16be", data.subarray(2)), encoding: "utf16be" };
    if (data.length >= 2 && data.length % 2 === 0) {
      let oddZeros = 0;
      let evenZeros = 0;
      for (let i = 0; i < data.length; i += 2) {
        if (data[i] === 0) evenZeros++;
        if (data[i + 1] === 0) oddZeros++;
      }
      const half = data.length / 2;
      if (oddZeros === half && evenZeros === 0) return { text: strict("utf-16le", data), encoding: "utf16le-plain" };
      if (evenZeros === half && oddZeros === 0) return { text: strict("utf-16be", data), encoding: "utf16be-plain" };
    }
    const text = strict("utf-8", data);
    // Text doesn't hold NUL characters; a file that does is treated as binary.
    return text.includes("\u0000") ? null : { text, encoding: "utf8" };
  } catch {
    return null;
  }
}

export function encodeText(text: string, encoding: TextEncoding): Buffer {
  if (encoding === "utf8") return Buffer.from(text, "utf8");
  if (encoding === "utf8-bom") return Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), Buffer.from(text, "utf8")]);
  const le = Buffer.from(text, "utf16le");
  if (encoding === "utf16le-plain") return le;
  if (encoding === "utf16le") return Buffer.concat([Buffer.from([0xff, 0xfe]), le]);
  const be = Buffer.from(le).swap16();
  return encoding === "utf16be-plain" ? be : Buffer.concat([Buffer.from([0xfe, 0xff]), be]);
}
