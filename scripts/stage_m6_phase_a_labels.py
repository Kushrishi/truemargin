"""Acquire only byte-identical frozen M6 calibration inputs, without registration."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

OFFICIAL_URL = (
    "https://www.cancerimagingarchive.net/wp-content/uploads/"
    "NCI-ISBI-2013-Prostate-Challenge-Training.zip"
)
LEGACY_URL = (
    "https://wiki.cancerimagingarchive.net/download/attachments/21267207/"
    "NCI-ISBI%202013%20Prostate%20Challenge%20-%20Training.zip?api=v2"
)
ARCHIVE_SHA256 = "c3436559b474c60e78633ea98601241f39cb27e30fb9d48b1d29f2821bfbf047"
PATIENT_RE = re.compile(r"(Prostate(?:3T|Dx)-01-\d{4})")


class TransportUnavailable(RuntimeError):
    pass


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "truemargin-research/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read()
    except (TimeoutError, urllib.error.URLError) as first:
        with tempfile.TemporaryDirectory(prefix="truemargin-label-transport-") as root:
            output = Path(root) / "archive.zip"
            process = subprocess.run(
                [
                    "curl",
                    "--fail",
                    "--location",
                    "--silent",
                    "--show-error",
                    "--connect-timeout",
                    "15",
                    "--max-time",
                    "60",
                    "--output",
                    str(output),
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=70,
                check=False,
            )
            if process.returncode != 0:
                raise TransportUnavailable(
                    f"{url}: urllib={type(first).__name__}:{first}; "
                    f"curl={process.returncode}:{process.stderr.strip()}"
                ) from first
            return output.read_bytes()


def verify_calibration_labels(payload: bytes, freeze: dict) -> dict[str, str]:
    if hashlib.sha256(payload).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("official training archive SHA-256 mismatch")
    patients = freeze["calibration"]
    if len(patients) != 30:
        raise ValueError("frozen calibration registry must contain exactly 30 anatomies")
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = {}
        for info in archive.infolist():
            match = PATIENT_RE.search(Path(info.filename).name)
            if info.is_dir() or not info.filename.lower().endswith(".nrrd") or match is None:
                continue
            patient = match.group(1)
            if patient in members:
                raise ValueError(f"duplicate training label: {patient}")
            members[patient] = info
        if len(members) != 60 or not set(patients).issubset(members):
            raise ValueError("official training archive membership drift")
        verified = {}
        # Evaluation labels are not decompressed or parsed by this transport preflight.
        for patient, row in sorted(patients.items()):
            observed = hashlib.sha256(archive.read(members[patient])).hexdigest()
            if observed != row["label_sha256"]:
                raise ValueError(f"frozen calibration label mismatch: {patient}")
            verified[patient] = observed
        return verified


def stage(freeze_path: Path, output: Path) -> dict:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("refusing to overwrite staged transport evidence")
    freeze_bytes = freeze_path.read_bytes()
    freeze = json.loads(freeze_bytes)
    errors = []
    for url in (OFFICIAL_URL, LEGACY_URL):
        try:
            payload = download(url)
        except TransportUnavailable as exc:
            errors.append(str(exc))
            continue
        verified = verify_calibration_labels(payload, freeze)
        record = {
            "schema_version": 1,
            "source_url": url,
            "official_dataset_page": "https://www.cancerimagingarchive.net/analysis-result/isbi-mr-prostate-2013/",
            "archive_sha256": ARCHIVE_SHA256,
            "archive_bytes": len(payload),
            "input_freeze_sha256": hashlib.sha256(freeze_bytes).hexdigest(),
            "calibration_label_sha256": verified,
            "prior_transport_errors": errors,
            "registration_performed": False,
            "evaluation_label_contents_inspected": False,
            "evaluation_results_accessed": False,
        }
        output.mkdir(parents=True, exist_ok=True)
        (output / "training-labels.zip").write_bytes(payload)
        (output / "training-labels.zip.sha256").write_text(ARCHIVE_SHA256 + "\n")
        (output / "label-transport.json").write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n"
        )
        return record
    raise TransportUnavailable(
        "all official training archive transports failed: " + "; ".join(errors)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--freeze", type=Path, default=Path("research/M6_PHASE_A_INPUT_FREEZE.json")
    )
    parser.add_argument("--output", type=Path, default=Path("inputs/m6_phase_a"))
    args = parser.parse_args()
    record = stage(args.freeze, args.output)
    print(
        "M6_PHASE_A_LABEL_CACHE=VERIFIED calibration_labels=30 "
        f"archive_sha256={record['archive_sha256']}"
    )


if __name__ == "__main__":
    main()
