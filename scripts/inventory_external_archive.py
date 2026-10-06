"""Verify archive identity and inspect ZIP names only; never read member payloads."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path


def inventory(path: Path, expected_md5: str) -> dict:
    md5, sha = hashlib.md5(), hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            md5.update(chunk)
            sha.update(chunk)
    if md5.hexdigest() != expected_md5:
        raise ValueError("official archive MD5 mismatch; do not extract")
    with zipfile.ZipFile(path) as archive:
        entries = [
            {"name": i.filename, "bytes": i.file_size, "crc32": i.CRC}
            for i in archive.infolist()
            if not i.is_dir()
        ]
    cases: dict[str, set[str]] = {}
    for item in entries:
        name = item["name"]
        if ".." in Path(name).parts or Path(name).is_absolute():
            raise ValueError("unsafe archive member path")
        match = re.search(r"(?:^|/)scans/case_(\d+)_(exp|insp)\.nii\.gz$", name)
        if match:
            cases.setdefault(match[1], set()).add(match[2])
    return {
        "archive": path.name,
        "size_bytes": path.stat().st_size,
        "md5": md5.hexdigest(),
        "sha256": sha.hexdigest(),
        "member_payloads_opened": False,
        "landmarks_accessed": False,
        "expiration_count": sum("exp" in s for s in cases.values()),
        "inspiration_count": sum("insp" in s for s in cases.values()),
        "complete_pair_ids": sorted(k for k, s in cases.items() if s == {"exp", "insp"}),
        "incomplete_pair_ids": sorted(k for k, s in cases.items() if s != {"exp", "insp"}),
        "entries": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--expected-md5", required=True)
    args = parser.parse_args()
    print(json.dumps(inventory(args.archive, args.expected_md5), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
