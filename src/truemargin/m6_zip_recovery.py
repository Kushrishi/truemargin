"""Recover exact frozen ZIP bytes; no candidate is accepted without its full digest."""

from __future__ import annotations

import hashlib
import io
import struct
import zipfile
from datetime import datetime, timedelta


def recover_frozen_zip(
    payload: bytes, expected_sha256: str, *, start: datetime, end: datetime
) -> tuple[bytes, dict[str, object]]:
    """Search historical DOS timestamps without changing member or other ZIP bytes.

    The search covers uniform timestamps and one ordered two-timestamp boundary,
    with a 2, 4, or 6 second gap. It is a bounded recovery procedure, not archive
    normalization: only exact equality to the existing archive SHA-256 succeeds.
    """
    if len(expected_sha256) != 64 or any(c not in "0123456789abcdef" for c in expected_sha256):
        raise ValueError("expected digest must be a full lowercase SHA-256")
    if start.tzinfo is not None or end.tzinfo is not None:
        raise ValueError("use naive UTC timestamps for the pinned acquisition interval")
    if start > end or (end - start).total_seconds() > 600:
        raise ValueError("invalid or unbounded timestamp recovery interval")
    observed = hashlib.sha256(payload).hexdigest()
    if observed == expected_sha256:
        return payload, {"recovery": "already_exact", "attempts": 0}
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = archive.infolist()
        if not members or len({m.filename for m in members}) != len(members):
            raise ValueError("archive must have nonempty unique members")
        local = [m.header_offset + 10 for m in members]
        central: list[int] = []
        position = archive.start_dir
        for member in members:
            if payload[member.header_offset : member.header_offset + 4] != b"PK\x03\x04":
                raise ValueError("invalid local ZIP header")
            if payload[position : position + 4] != b"PK\x01\x02":
                raise ValueError("invalid central ZIP header")
            central.append(position + 12)
            name_size, extra_size, comment_size = struct.unpack_from("<HHH", payload, position + 28)
            position += 46 + name_size + extra_size + comment_size
    offsets = tuple(zip(local, central, strict=True))
    candidate = bytearray(payload)
    first = start - timedelta(seconds=start.second % 2, microseconds=start.microsecond)
    attempts = 0

    def stamp(moment: datetime) -> bytes:
        if not 1980 <= moment.year <= 2107:
            raise ValueError("timestamp outside ZIP DOS range")
        return struct.pack(
            "<HH",
            (moment.hour << 11) | (moment.minute << 5) | (moment.second // 2),
            ((moment.year - 1980) << 9) | (moment.month << 5) | moment.day,
        )

    # Uniform timestamps are tested first because most small archives finish
    # inside one two-second DOS timestamp bin.
    times: list[datetime] = []
    moment = first
    while moment <= end:
        times.append(moment)
        moment += timedelta(seconds=2)
    for gap in (0, 2, 4, 6):
        for moment in times:
            later = moment + timedelta(seconds=gap)
            if later > end:
                continue
            stamps = (stamp(moment), stamp(later))
            splits = (len(offsets),) if gap == 0 else range(1, len(offsets))
            for split in splits:
                for index, (local_offset, central_offset) in enumerate(offsets):
                    value = stamps[int(index >= split)]
                    candidate[local_offset : local_offset + 4] = value
                    candidate[central_offset : central_offset + 4] = value
                attempts += 1
                if hashlib.sha256(candidate).hexdigest() == expected_sha256:
                    recovered = bytes(candidate)
                    return recovered, {
                        "recovery": "exact_frozen_archive_digest",
                        "first_timestamp_utc": moment.isoformat(),
                        "second_timestamp_utc": later.isoformat(),
                        "member_boundary": split,
                        "member_count": len(offsets),
                        "attempts": attempts,
                    }
    raise RuntimeError(
        f"historical ZIP identity remains unresolved: observed={observed} "
        f"expected={expected_sha256}"
    )
