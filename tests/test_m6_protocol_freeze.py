"""Prospective invariants for the frozen M6 calibration protocol."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_m6_split_is_exact_balanced_and_outcome_blind():
    record = _load("research/M6_SPLIT.json")
    roles = record["roles"]
    rule = record["assignment_rule"]

    assert rule["outcome_information_used"] is False
    assert set(roles) == {"prostate_3t", "prostate_diagnosis"}

    all_patients: list[str] = []
    for source in rule["sources"]:
        calibration = roles[source]["calibration"]
        evaluation = roles[source]["evaluation"]
        assert len(calibration) == 15
        assert len(evaluation) == 15
        assert not (set(calibration) & set(evaluation))
        all_patients.extend(calibration)
        all_patients.extend(evaluation)

        ranked = sorted(
            (
                hashlib.sha256((rule["salt"] + patient_id).encode()).hexdigest(),
                patient_id,
            )
            for patient_id in calibration + evaluation
        )
        assert calibration == [patient_id for _, patient_id in ranked[:15]]
        assert evaluation == [patient_id for _, patient_id in ranked[15:]]

    assert len(all_patients) == 60
    assert len(set(all_patients)) == 60
    assert record["counts"]["calibration"] == 30
    assert record["counts"]["evaluation"] == 30
    assert record["identity_policy"]["duplicated_dicom_uids_in_split"] is False


def test_m6_geometry_gate_is_complete_before_split_freeze():
    record = _load("research/M6_GEOMETRY_ELIGIBILITY_COMPLETE.json")
    assert record["status"] == "complete"
    assert record["training_anatomies"] == 60
    assert record["eligible_count"] == 60
    assert record["ineligible_patient_ids"] == []
    assert all(value == 0 for value in record["criteria_failures"].values())
    assert record["known_0055"]["eligible"] is True
    assert record["known_0055"]["array_size_equal"] is False
    assert record["known_0055"]["out_of_domain_foreground_voxels"] == 0


def test_m6_prior_substrate_exact_uid_overlap_is_zero():
    record = _load("research/M6_PRIOR_SUBSTRATE_OVERLAP_AUDIT.json")
    assert record["status"] == "complete"
    assert record["exact_overlap"]["series_instance_uid_count"] == 0
    assert record["exact_overlap"]["series_instance_uids"] == []
    assert record["exact_overlap"]["study_instance_uid_count"] == 0
    assert record["exact_overlap"]["study_instance_uids"] == []


def test_m6_protocol_freeze_keeps_result_bearing_execution_closed():
    record = _load("research/M6_PROTOCOL_FREEZE.json")
    assert record["status"] == "frozen_pre_result"

    design = record["frozen_design"]
    assert design["m6_subjects"] == 60
    assert design["calibration_subjects"] == 30
    assert design["evaluation_subjects"] == 30
    assert design["calibration_per_source"] == 15
    assert design["evaluation_per_source"] == 15
    assert design["points_per_anatomy"] == 50
    assert design["deformation_replicates_per_anatomy"] == 1
    assert design["hcp_stratification"] == "source_key"
    assert design["primary_nominal_coverage"] == 0.90
    assert design["primary_abstention_rule"] == "none"

    auth = record["next_authorized_work"]
    assert auth["synthetic_deformation_generation_authorized"] is True
    assert auth["roi_warp_and_point_sampling_authorized"] is True
    assert auth["forward_registration_authorized"] is False
    assert auth["reverse_registration_authorized"] is False
    assert auth["sigma_computation_authorized"] is False
    assert auth["ice_computation_authorized"] is False
    assert auth["calibration_fit_authorized"] is False
    assert auth["evaluation_authorized"] is False
