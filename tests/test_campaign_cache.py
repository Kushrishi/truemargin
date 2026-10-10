"""Production receipt/cache integration with synthetic fields; no clinical data."""

import copy
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pytest

from truemargin import campaign_cache as campaign
from truemargin import ensemble
from truemargin import registration_member as producer
from truemargin.ensemble import summarize_fields
from truemargin.hyperparameter import CONFIGS, config_id
from truemargin.member_retention import retain_registration_member


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
