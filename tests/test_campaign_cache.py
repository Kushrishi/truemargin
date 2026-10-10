"""Production receipt/cache integration with synthetic fields; no clinical data."""

import copy
import json
import shutil
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pytest

from truemargin import campaign_cache as campaign
from truemargin import ensemble
from truemargin import member_transport as transport
from truemargin import registration_member as producer
from truemargin.ensemble import summarize_fields
from truemargin.hyperparameter import CONFIGS, config_id
from truemargin.member_retention import retain_registration_member
from truemargin.provenance import _sha256_file


@pytest.fixture
def group(tmp_path, monkeypatch):
    def synthetic(fixed, moving, **options):
        options["progress_callback"](0, -1.0)
        options["completion_callback"](
            {"optimizer_stop_condition": "synthetic", "optimizer_iteration": 1}
        )
        field = np.arange(72, dtype=np.float64).reshape(3, 2, 3, 4) / 1000
        return field + options["metric_bins"] / 1000 + options["gradient_convergence_tolerance"]

    monkeypatch.setattr(producer, "baseline_bspline_registration", synthetic)
    members = []
    for bins, tolerance in CONFIGS:
        member_id = config_id(bins, tolerance)
        source = tmp_path / member_id
        producer.execute_registration_member(
            source,
            fixed=np.zeros((2, 3, 4), dtype=np.int16),
            moving=np.ones((2, 3, 4), dtype=np.int16),
            settings=producer.RegistrationSettings(
                3, 15, (0.97, 0.97, 2.5), False, bins, tolerance
            ),
            repo_root=Path(__file__).resolve().parents[1],
            member_id=member_id,
            case_id="4DCT7",
            fixed_image_id="T50",
            moving_image_id="T00",
        )
        manifest = json.loads((source / "started.json").read_text())["manifest"]
        receipt = retain_registration_member(
            source, tmp_path / (member_id + "-retained"), expected_manifest=manifest
        )
        members.append(campaign.RetainedMember(source, manifest, receipt))
    return members


def test_full_producer_to_cache_parity_and_frozen_order(group):
    arrays = [np.load(member.directory / "field/field.npy") for member in group]
    expected = summarize_fields(arrays)
    # Reverse caller order and cross a final singleton spatial block.
    result = campaign.summarize_campaign_group(list(reversed(group)), block_voxels=23)
    for actual, reference in zip(result, expected, strict=True):
        np.testing.assert_array_equal(actual, reference)


def test_recovered_member_survives_missing_original(group, tmp_path):
    member = group[0]
    restored = campaign.recover_campaign_member(member, tmp_path / "restored")
    member.directory.rename(tmp_path / "offline-original")
    assert restored.receipt is member.receipt
    assert (
        campaign.verify_campaign_member(restored).member_id
        == member.expected_manifest["artifact_id"]
    )
    with pytest.raises(FileExistsError):
        campaign.recover_campaign_member(restored, restored.directory)


def test_concurrent_recovery_has_one_destination_owner(group, tmp_path):
    destination = tmp_path / "shared-destination"

    def recover():
        try:
            campaign.recover_campaign_member(group[0], destination)
            return "verified"
        except FileExistsError:
            return "already_claimed"

    with ThreadPoolExecutor(max_workers=8) as workers:
        results = list(workers.map(lambda _: recover(), range(8)))
    assert results.count("verified") == 1
    assert results.count("already_claimed") == 7
    restored = campaign.RetainedMember(destination, group[0].expected_manifest, group[0].receipt)
    assert campaign.verify_campaign_member(restored)


def test_summary_never_stacks_full_volume(group, monkeypatch):
    original = ensemble.summarize_fields
    observed = []

    def bounded(fields):
        observed.append(fields[0].shape[-1])
        assert len(fields) == 9
        assert all(field.shape == (3, 5) or field.shape == (3, 4) for field in fields)
        return original(fields)

    monkeypatch.setattr(ensemble, "summarize_fields", bounded)
    campaign.summarize_campaign_group(group, block_voxels=5)
    assert observed == [5, 5, 5, 5, 4]


def test_interrupted_copy_preserved_without_retry(group, tmp_path, monkeypatch):
    member = group[0]
    destination = tmp_path / "interrupted"
    original = shutil.copyfileobj
    calls = 0

    def interrupted(reader, writer, length):
        nonlocal calls
        calls += 1
        if calls == 3:
            writer.write(reader.read(32))
            raise OSError("synthetic destination loss")
        return original(reader, writer, length)

    monkeypatch.setattr(shutil, "copyfileobj", interrupted)
    with pytest.raises(OSError):
        campaign.recover_campaign_member(member, destination)
    assert not (destination / "completed.json").exists()
    assert (destination / "field/field.npy.partial").stat().st_size == 32
    with pytest.raises(FileExistsError):
        campaign.recover_campaign_member(member, destination)
    assert calls == 3
    # A different destination can recover the original; this never registers.
    monkeypatch.setattr(shutil, "copyfileobj", original)
    assert campaign.verify_campaign_member(
        campaign.recover_campaign_member(member, tmp_path / "restored")
    )


def test_source_change_during_recovery_cannot_replace_independent_receipt(
    group, tmp_path, monkeypatch
):
    original = campaign.retain_registration_member

    def changed_source(source, destination, **kwargs):
        with (source / "progress.jsonl").open("a") as handle:
            handle.write('{"unexpected_late_event":true}\n')
        return original(source, destination, **kwargs)

    monkeypatch.setattr(campaign, "retain_registration_member", changed_source)
    destination = tmp_path / "changed-copy"
    with pytest.raises(ValueError, match="independent receipt"):
        campaign.recover_campaign_member(group[0], destination)
    # A copy may exist, but it is not accepted against the independent record.
    with pytest.raises(ValueError, match="producer receipt"):
        campaign.verify_campaign_member(
            campaign.RetainedMember(destination, group[0].expected_manifest, group[0].receipt)
        )


@pytest.mark.parametrize(
    ("setting", "value"),
    [
        ("mesh_size", 4),
        ("max_iterations", 16),
        ("center_first", True),
        ("metric_bins", 100),
        ("gradient_convergence_tolerance", 1e-7),
    ],
)
def test_off_protocol_configuration_rejected(group, setting, value):
    group[0].expected_manifest["parameters"]["registration"][setting] = value
    with pytest.raises(ValueError, match="frozen hyperparameter grid"):
        campaign.summarize_campaign_group(group)


@pytest.mark.parametrize(
    "change", ["missing", "duplicate", "direction", "source", "packages", "spacing"]
)
def test_incomplete_or_mixed_groups_rejected_before_summary(group, monkeypatch, change):
    members = copy.deepcopy(group)
    if change == "missing":
        members.pop()
    elif change == "duplicate":
        members[-1] = members[0]
    else:
        manifest = members[-1].expected_manifest
        if change == "direction":
            data = manifest["data_identity"]
            data["fixed_image_id"], data["moving_image_id"] = "T00", "T50"
            data["fixed"], data["moving"] = data["moving"], data["fixed"]
        if change == "source":
            manifest["code_hash"] = "0" * 64
        if change == "packages":
            manifest["parameters"]["packages"]["numpy"] = "other-version"
        if change == "spacing":
            manifest["parameters"]["registration"]["spacing"][0] = 2.0
    monkeypatch.setattr(
        campaign, "summarize_fields_blockwise", lambda *a, **k: pytest.fail("summary must not run")
    )
    with pytest.raises(ValueError):
        campaign.summarize_campaign_group(members)


@pytest.mark.parametrize(
    "kind", ["tampered", "unknown", "failed", "wrong_receipt", "wrong_manifest"]
)
def test_invalid_member_cannot_enter_summary(group, kind):
    member = group[-1]
    if kind == "tampered":
        path = member.directory / "field/field.npy"
        with path.open("ab") as handle:
            handle.write(b"corruption")
    if kind == "unknown":
        (member.directory / "completed.json").unlink()
    if kind == "failed":
        (member.directory / "failed.json").write_text("{}")
    if kind == "wrong_receipt":
        member.receipt["files"]["field/field.npy"]["sha256"] = "0" * 64
    if kind == "wrong_manifest":
        member.expected_manifest["data_identity"]["fixed"]["sha256"] = "0" * 64
    with pytest.raises(ValueError):
        campaign.summarize_campaign_group(group)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 1000.0, 1e308])
def test_invalid_field_fails_full_scan(value):
    field = np.zeros((3, 2, 3, 4))
    field[:, -1, -1, -1] = value
    with pytest.raises(ValueError):
        campaign._check_field(field, (0.97, 0.97, 2.5), 5)


@pytest.mark.parametrize("block", [True, 0, 1, 2.5])
def test_invalid_block_size_rejected_without_io(block):
    with pytest.raises(ValueError, match="block_voxels"):
        campaign.summarize_campaign_group([], block_voxels=block)


@pytest.fixture
def packet(group, tmp_path):
    member = group[0]
    manifest = tmp_path / "expected-manifest.json"
    receipt = tmp_path / "producer-receipt.json"
    manifest.write_text(json.dumps(member.expected_manifest))
    receipt.write_text(json.dumps(member.receipt))
    pins = dict(manifest_sha256=_sha256_file(manifest), receipt_sha256=_sha256_file(receipt))
    path = tmp_path / "packet.zip"
    transport.pack_member(member.directory, manifest, receipt, path, **pins)
    return path, pins, member


def test_transport_cli_recovers_without_original_or_registration(packet, tmp_path, monkeypatch):
    path, pins, member = packet
    member.directory.rename(tmp_path / "original-offline")
    monkeypatch.setattr(
        producer, "baseline_bspline_registration", lambda *a, **k: pytest.fail("must not register")
    )
    staging, destination, report = [tmp_path / n for n in ("staging", "recovered", "report.json")]
    args = [
        "recover",
        "--packet",
        str(path),
        "--staging",
        str(staging),
        "--destination",
        str(destination),
        "--report",
        str(report),
    ]
    for name, value in pins.items():
        args += ["--" + name.replace("_", "-"), value]
    assert transport.main(args) == 0
    saved = json.loads(report.read_text())
    assert saved["status"] == "recovered_verified"
    assert saved["producer_git_sha"] == member.expected_manifest["git_sha"]
    assert saved["field_sha256"] == member.receipt["files"]["field/field.npy"]["sha256"]
    assert saved["readback_after_staging_renamed"]
    assert saved["host_distinctness"] == "requires_independent_producer_host_record"
    assert saved["held_out_access_safe"] is False
    assert not staging.exists()
    assert transport.main(args) == 2


@pytest.mark.parametrize("change", ["extra", "traversal", "duplicate", "symlink", "size", "pin"])
def test_transport_rejects_bad_packet_before_claim(packet, tmp_path, change):
    path, pins, _ = packet
    modified = tmp_path / "modified.zip"
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(modified, "w") as target:
        for info in source.infolist():
            data = source.read(info)
            if change == "size" and info.filename == "member/progress.jsonl":
                data += b"extra"
            if change == "symlink" and info.filename == "member/started.json":
                info.external_attr = 0o120777 << 16
            target.writestr(info, data)
        if change in {"extra", "traversal", "duplicate"}:
            name = {
                "extra": "landmarks.txt",
                "traversal": "../outside",
                "duplicate": "member/started.json",
            }[change]
            target.writestr(name, b"unexpected")
    if change == "pin":
        pins["manifest_sha256"] = "0" * 64
    destination = tmp_path / "unpacked"
    with pytest.raises(ValueError):
        transport.unpack_member(modified, destination, **pins)
    assert not destination.exists()


def test_transport_tamper_cannot_be_accepted_with_same_size(packet, tmp_path):
    path, pins, _ = packet
    modified = tmp_path / "tampered.zip"
    with zipfile.ZipFile(path) as source, zipfile.ZipFile(modified, "w") as target:
        for info in source.infolist():
            data = source.read(info)
            if info.filename == "member/field/field.npy":
                data = data[:-1] + bytes([data[-1] ^ 1])
            target.writestr(info, data)
    destination = tmp_path / "rejected"
    with pytest.raises(ValueError, match="independent receipt"):
        transport.unpack_member(modified, destination, **pins)
    assert (destination / "field/field.npy.partial").exists()
    assert not (destination / "completed.json").exists()


def test_transport_interruption_preserved_and_existing_attempt_refused(
    packet, tmp_path, monkeypatch
):
    path, pins, _ = packet
    destination = tmp_path / "interrupted-transport"

    def interrupt(reader, writer, length):
        writer.write(reader.read(8))
        raise OSError("synthetic interrupted transfer")

    monkeypatch.setattr(shutil, "copyfileobj", interrupt)
    with pytest.raises(OSError):
        transport.unpack_member(path, destination, **pins)
    assert (destination / "started.json.partial").stat().st_size == 8
    assert not (destination / "completed.json").exists()
    with pytest.raises(FileExistsError):
        transport.unpack_member(path, destination, **pins)


def test_transport_records_cannot_self_authenticate():
    with pytest.raises(ValueError, match="independent pin"):
        transport._pinned_record(b'{"changed":true}', "0" * 64)
    import hashlib

    data = b'{"a":1,"a":2}'
    with pytest.raises(ValueError, match="duplicate JSON"):
        transport._pinned_record(data, hashlib.sha256(data).hexdigest())


def test_outcome_blind_grid_cost_and_diversity(group, monkeypatch):
    monkeypatch.setattr(
        campaign, "summarize_fields_blockwise", lambda *a, **k: pytest.fail("no summary allocation")
    )
    report = campaign.describe_campaign_group(list(reversed(group)), block_voxels=5)
    assert len(report["members"]) == 9
    assert len(report["pairwise_field_differences"]) == 36
    assert report["raw_field_payload_bytes"] == 9 * 72 * 8
    assert report["mean_spread_payload_bytes"] == 24 * 4 * 8
    assert report["full_campaign_authorized"] is False
    assert report["numerical_landmarks_opened"] is False
    assert all(row["producer_peak_rss_bytes"] is None for row in report["members"])
    assert all(row["iteration_cap_observed"] is False for row in report["members"])
    arrays = [np.load(member.directory / "field/field.npy") for member in group]
    from itertools import combinations

    for row, (left, right) in zip(
        report["pairwise_field_differences"], combinations(range(9), 2), strict=True
    ):
        delta = arrays[left] - arrays[right]
        np.testing.assert_allclose(
            row["rms_vector_difference_mm"], np.sqrt(np.mean(np.sum(delta**2, axis=0)))
        )
        np.testing.assert_allclose(
            row["maximum_vector_difference_mm"], np.sqrt(np.max(np.sum(delta**2, axis=0)))
        )


def test_outcome_blind_grid_cannot_describe_survivors(group):
    with pytest.raises(ValueError, match="exactly nine"):
        campaign.describe_campaign_group(group[:-1])


@pytest.mark.parametrize("collision", ["destination", "report", "existing", "dangling"])
def test_transport_offline_collision_rejected_before_copy(packet, tmp_path, collision):
    path, pins, _ = packet
    staging = tmp_path / "staging"
    offline = tmp_path / "staging-offline"
    destination, report = tmp_path / "restored", tmp_path / "report.json"
    if collision == "destination":
        destination = offline
    elif collision == "report":
        report = offline / "report.json"
    elif collision == "existing":
        offline.mkdir()
    else:
        offline.symlink_to(tmp_path / "missing")
    args = [
        "recover",
        "--packet",
        str(path),
        "--staging",
        str(staging),
        "--destination",
        str(destination),
        "--report",
        str(report),
    ]
    for name, value in pins.items():
        args += ["--" + name.replace("_", "-"), value]
    assert transport.main(args) == 2
    assert not staging.exists()
    assert not report.is_file()
