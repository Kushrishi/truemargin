"""Transport completed member bytes using independently supplied record hashes.

No image archives, landmarks, registration, retry, or campaign launch is supported.
Pins must come from reviewed records outside the packet, not from the packet itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import stat
import sys
import zipfile
from pathlib import Path

from truemargin.campaign_cache import (
    RetainedMember,
    recover_campaign_member,
    verify_campaign_member,
)
from truemargin.member_retention import FILES, _regular_file
from truemargin.provenance import _sha256_file

RECORDS = ("expected-manifest.json", "producer-receipt.json")
PACKET_FILES = (*RECORDS, *("member/" + name for name in FILES))
MAX_RECORD_BYTES = 1024 * 1024


def _pinned_record(data: bytes, expected: str) -> dict:
    if (
        not isinstance(expected, str)
        or len(expected) != 64
        or any(c not in "0123456789abcdef" for c in expected)
    ):
        raise ValueError("independent lowercase SHA-256 record pin required")
    if len(data) > MAX_RECORD_BYTES or hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("record bytes differ from independent pin")

    def reject(value):
        raise ValueError(f"nonfinite JSON: {value}")

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    record = json.loads(data, parse_constant=reject, object_pairs_hook=unique)
    if not isinstance(record, dict):
        raise ValueError("record must be an object")
    return record


def _record_bytes(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_RECORD_BYTES:
        raise ValueError("bounded regular record file required")
    return path.read_bytes()


def pack_member(
    directory: Path,
    manifest_path: Path,
    receipt_path: Path,
    packet: Path,
    *,
    manifest_sha256: str,
    receipt_sha256: str,
) -> dict:
    """Write only the five producer files and two hash-pinned records, once."""
    manifest_bytes, receipt_bytes = _record_bytes(manifest_path), _record_bytes(receipt_path)
    manifest = _pinned_record(manifest_bytes, manifest_sha256)
    receipt = _pinned_record(receipt_bytes, receipt_sha256)
    member = RetainedMember(directory, manifest, receipt)
    verify_campaign_member(member)
    # Mode x preserves any previous complete or interrupted transfer attempt.
    with zipfile.ZipFile(packet, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
        archive.writestr(RECORDS[0], manifest_bytes)
        archive.writestr(RECORDS[1], receipt_bytes)
        for name in FILES:
            archive.write(_regular_file(directory, name), "member/" + name)
    # Check the immutable source again, as the packet is not itself a trust root.
    verify_campaign_member(member)
    return {"packet_sha256": _sha256_file(packet), "packet_bytes": packet.stat().st_size}


def unpack_member(
    packet: Path,
    destination: Path,
    *,
    manifest_sha256: str,
    receipt_sha256: str,
) -> RetainedMember:
    """Strict allowlist extraction with bounded streaming and retained failures.

    Receipt sizes bound decompression before destination creation. Completion is
    copied last; all extracted bytes and the entire field are then verified.
    Synthetic interruption tests do not establish filesystem power-loss behavior.
    """
    if packet.is_symlink() or not packet.is_file():
        raise ValueError("regular packet file required")
    with zipfile.ZipFile(packet) as archive:
        infos = archive.infolist()
        if len(infos) != len(PACKET_FILES) or {i.filename for i in infos} != set(PACKET_FILES):
            raise ValueError(
                "packet must contain exactly the allowlisted files, without duplicates"
            )
        for info in infos:
            mode = info.external_attr >> 16
            if info.is_dir() or stat.S_IFMT(mode) not in (0, stat.S_IFREG) or info.flag_bits & 1:
                raise ValueError("packet requires regular unencrypted files")
        records = []
        for name, pin in zip(RECORDS, (manifest_sha256, receipt_sha256), strict=True):
            if archive.getinfo(name).file_size > MAX_RECORD_BYTES:
                raise ValueError("packet record too large")
            records.append(_pinned_record(archive.read(name), pin))
        manifest, receipt = records
        if receipt.get("schema_version") != "registration-member-retention/1":
            raise ValueError("unsupported retention receipt")
        files = receipt.get("files")
        if not isinstance(files, dict) or set(files) != set(FILES):
            raise ValueError("receipt must identify exactly the producer files")
        for name in FILES:
            if not isinstance(files[name], dict):
                raise ValueError("receipt file record must be an object")
            size = files[name].get("bytes")
            if (
                type(size) is not int
                or size < 0
                or archive.getinfo("member/" + name).file_size != size
            ):
                raise ValueError("packet size differs from independent receipt")
        destination.mkdir()
        (destination / "field").mkdir()
        for name in FILES:
            path = destination / name
            partial = path.with_name(path.name + ".partial")
            with archive.open("member/" + name) as reader, partial.open("xb") as writer:
                shutil.copyfileobj(reader, writer, length=1024 * 1024)
                writer.flush()
                os.fsync(writer.fileno())
            if (
                partial.stat().st_size != files[name]["bytes"]
                or _sha256_file(partial) != files[name]["sha256"]
            ):
                raise ValueError("transported bytes differ from independent receipt")
            partial.rename(path)
    member = RetainedMember(destination, manifest, receipt)
    verify_campaign_member(member)
    return member


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    pack = commands.add_parser("pack")
    pack.add_argument("--member", type=Path, required=True)
    pack.add_argument("--manifest", type=Path, required=True)
    pack.add_argument("--receipt", type=Path, required=True)
    pack.add_argument("--packet", type=Path, required=True)
    recover = commands.add_parser("recover")
    recover.add_argument("--packet", type=Path, required=True)
    recover.add_argument("--staging", type=Path, required=True)
    recover.add_argument("--destination", type=Path, required=True)
    recover.add_argument("--report", type=Path, required=True)
    for command in (pack, recover):
        command.add_argument("--manifest-sha256", required=True)
        command.add_argument("--receipt-sha256", required=True)
    args = parser.parse_args(argv)
    pins = dict(manifest_sha256=args.manifest_sha256, receipt_sha256=args.receipt_sha256)
    try:
        if args.command == "pack":
            result = pack_member(args.member, args.manifest, args.receipt, args.packet, **pins)
        else:
            # Refuse before copying if output names collide or already exist.
            offline = args.staging.with_name(args.staging.name + "-offline")
            outputs = (args.staging, offline, args.destination, args.report)
            resolved = [p.resolve() for p in outputs]
            if (
                len(set(resolved)) != 4
                or any(p.exists() or p.is_symlink() for p in outputs)
                or any(a in b.parents for a in resolved for b in resolved if a != b)
            ):
                raise FileExistsError(
                    "fresh, distinct staging, offline staging, destination and report required"
                )
            member = unpack_member(args.packet, args.staging, **pins)
            restored = recover_campaign_member(member, args.destination)
            # Prove readback does not depend on the original directory name.
            args.staging.rename(offline)
            verify_campaign_member(restored)
            result = {
                "schema": "registration-member-transport-readback/1",
                "status": "recovered_verified",
                "consumer_host": platform.platform(),
                "consumer_python": sys.version,
                "consumer_module_sha256": _sha256_file(Path(__file__)),
                "packet_sha256": _sha256_file(args.packet),
                **pins,
                "producer_git_sha": restored.expected_manifest["git_sha"],
                "member_id": restored.expected_manifest["artifact_id"],
                "field_sha256": restored.receipt["files"]["field/field.npy"]["sha256"],
                "restored_directory": str(args.destination.resolve()),
                "staging_offline_directory": str(offline.resolve()),
                "readback_after_staging_renamed": True,
                "host_distinctness": "requires_independent_producer_host_record",
                "registration_executed": False,
                "numerical_landmarks_opened": False,
                "held_out_access_safe": False,
                "convergence": "not_established",
                "accuracy": "not_evaluated",
                "campaign_credit_assigned": False,
            }
            with args.report.open("x", encoding="utf-8") as writer:
                writer.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
                writer.flush()
                os.fsync(writer.fileno())
        print(json.dumps(result, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        print(f"Recovery/transport rejected; preserve attempt: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
