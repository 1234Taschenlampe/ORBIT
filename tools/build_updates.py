#!/usr/bin/env python3
"""Build ORBIT's public update index from APK files that actually exist.
Standard-library-only; Python 3.9+. This is metadata inspection, NOT APK signature verification.
"""
import datetime
import hashlib
import json
import re
import struct
import zipfile
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
APK_DIR = ROOT / "apks"
OUT = ROOT / "updates.json"
REPO = "1234Taschenlampe/ORBIT"
MAX_BYTES = 100 * 1024 * 1024
U32 = (1 << 32) - 1


def u16(b, p):
    return struct.unpack_from("<H", b, p)[0]


def u32(b, p):
    return struct.unpack_from("<I", b, p)[0]


def str_len8(b, p):
    n = b[p]
    p += 1
    if n & 128:
        n = ((n & 127) << 8) | b[p]
        p += 1
    return n, p


def str_len16(b, p):
    n = u16(b, p)
    p += 2
    if n & 0x8000:
        n = ((n & 0x7fff) << 16) | u16(b, p)
        p += 2
    return n, p


def apk_manifest(data):
    """Extract package, versionCode, versionName, min/target SDK and debuggable."""
    if u16(data, 0) != 3:
        raise ValueError("Not binary Android XML")
    strings, attributes, sdk, debuggable = [], {}, {}, False
    p = 8
    while p + 8 <= len(data):
        typ, hsize, size = u16(data, p), u16(data, p + 2), u32(data, p + 4)
        if size < hsize or p + size > len(data):
            raise ValueError("Invalid Android XML chunk")
        if typ == 1:
            count, flags, strstart = u32(data, p + 8), u32(data, p + 16), u32(data, p + 20)
            strings = []
            for i in range(count):
                q = p + strstart + u32(data, p + hsize + i * 4)
                if flags & 0x100:
                    _, q = str_len8(data, q)
                    n, q = str_len8(data, q)
                    value = data[q:q + n].decode("utf-8", "replace")
                else:
                    n, q = str_len16(data, q)
                    value = data[q:q + n * 2].decode("utf-16-le", "replace")
                strings.append(value)
        if typ == 0x102:
            tag = strings[u32(data, p + 20)]
            start = p + 16 + u16(data, p + 24)
            stride, count = u16(data, p + 26), u16(data, p + 28)
            vals = {}
            for i in range(count):
                at = start + i * stride
                name, raw, t, payload = u32(data, at + 4), u32(data, at + 8), data[at + 15], u32(data, at + 16)
                key = strings[name]
                if raw != U32:
                    val = strings[raw]
                elif t == 3:
                    val = strings[payload]
                elif t == 0x12:
                    val = bool(payload)
                elif t in (0x10, 0x11):
                    val = payload
                else:
                    val = None
                vals[key] = val
            if tag == "manifest":
                attributes = vals
            elif tag == "uses-sdk":
                sdk = vals
            elif tag == "application":
                debuggable = vals.get("debuggable", False)
        p += size
    package = attributes.get("package")
    version_code = attributes.get("versionCode")
    if not package or not isinstance(version_code, int):
        raise ValueError("APK missing package or integer versionCode")
    return {
        "packageName": package,
        "versionCode": version_code,
        "versionName": str(attributes.get("versionName") or version_code),
        "minSdk": sdk.get("minSdkVersion"),
        "targetSdk": sdk.get("targetSdkVersion"),
        "debuggable": bool(debuggable),
    }


def length_item(buf, off):
    n = u32(buf, off)
    end = off + 4 + n
    if end > len(buf):
        raise ValueError("Invalid signing data length")
    return buf[off + 4:end], end


def signing_fingerprint(path):
    """Extract first leaf signing certificate from APK Signature Scheme v2/v3.
    Certificate fingerprint extraction does not verify the APK's signature.
    """
    with path.open("rb") as f:
        f.seek(0, 2)
        file_size = f.tell()
        f.seek(max(0, file_size - 65557))
        tail = f.read()
        eocd = tail.rfind(b"PK\x05\x06")
        if eocd < 0:
            raise ValueError("Missing ZIP end of central directory")
        central = u32(tail, eocd + 16)
        if central < 24:
            raise ValueError("No APK signing block")
        f.seek(central - 24)
        footer = f.read(24)
        if footer[8:] != b"APK Sig Block 42":
            raise ValueError("No APK v2/v3 signing block")
        size = struct.unpack_from("<Q", footer, 0)[0]
        if size > file_size or size > MAX_BYTES:
            raise ValueError("Invalid APK signing block size")
        f.seek(central - (size + 8))
        block = f.read(size + 8)

    off = 8
    while off + 12 < len(block) - 24:
        n = struct.unpack_from("<Q", block, off)[0]
        off += 8
        if n < 4 or off + n > len(block) - 24:
            raise ValueError("Invalid signing block pair")
        identifier = u32(block, off)
        payload = block[off + 4:off + n]
        off += n
        if identifier in (0x7109871a, 0xf05368c0):
            signers, _ = length_item(payload, 0)
            first_signer, _ = length_item(signers, 0)
            signed_data, _ = length_item(first_signer, 0)
            _, cursor = length_item(signed_data, 0)
            certificate_sequence, _ = length_item(signed_data, cursor)
            first_certificate, _ = length_item(certificate_sequence, 0)
            return hashlib.sha256(first_certificate).hexdigest()
    raise ValueError("No v2/v3 signer found")


def main():
    catalog = json.loads((ROOT / "apps.json").read_text(encoding="utf-8"))
    known = {}
    for app in catalog["apps"]:
        for build in app["builds"]:
            filename = build[0]
            if filename in known:
                raise ValueError("Duplicate catalog filename: " + filename)
            known[filename] = {"appId": app["id"], "appName": app["name"]}
    records = []
    ignored = []
    for file in sorted(APK_DIR.glob("*.apk")) if APK_DIR.is_dir() else []:
        if not re.fullmatch(r"[a-zA-Z0-9_.()+-]+\.apk", file.name):
            ignored.append(file.name + ": invalid filename")
            continue
        if file.name not in known:
            ignored.append(file.name + ": not listed in apps.json")
            continue
        if file.stat().st_size > MAX_BYTES:
            raise ValueError(file.name + ": GitHub file size limit exceeded")
        with zipfile.ZipFile(file) as z:
            bad = z.testzip()
            if bad is not None:
                raise ValueError(file.name + ": ZIP corruption at " + bad)
            manifest = apk_manifest(z.read("AndroidManifest.xml"))
        signer = signing_fingerprint(file)
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        tag = "debug" if manifest["debuggable"] else "beta" if "beta" in file.name.lower() else "release"
        records.append({
            **known[file.name], **manifest,
            "filename": file.name,
            "size": file.stat().st_size,
            "sha256": digest,
            "signerSha256": signer,
            "channel": tag,
            "autoUpdateEligible": tag == "release",
            "url": f"https://raw.githubusercontent.com/{REPO}/main/apks/{quote(file.name)}",
        })
    # All builds remain visible; only one version per package + signing key
    # can be a proposed update for a given installed app.
    eligible = {}
    for item in records:
        if item["autoUpdateEligible"]:
            key = (item["packageName"], item["signerSha256"])
            if key not in eligible or item["versionCode"] > eligible[key]["versionCode"]:
                eligible[key] = item
    for item in records:
        item["recommendedForInstalledSigner"] = eligible.get(
            (item["packageName"], item["signerSha256"]), {}
        ).get("filename") == item["filename"]
    out = {
        "schemaVersion": 1,
        "repository": REPO,
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "notice": "Static metadata only. Device compatibility and APK signatures are not independently verified.",
        "artifacts": records,
        "ignored": ignored,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"ORBIT: {len(records)} APKs indexed, {len(ignored)} ignored")
    for reason in ignored:
        print("SKIPPED: " + reason)


if __name__ == "__main__":
    main()
