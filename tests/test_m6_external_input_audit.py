"""Unit tests for the metadata-only M6 external-input audit."""

from __future__ import annotations

import io
import runpy
import zipfile
from pathlib import Path
from typing import Any

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "audit_m6_external_inputs.py"
SCRIPT = runpy.run_path(str(SCRIPT_PATH), run_name='m6_external_input_audit_test')


def _function(name: str):
    return SCRIPT[name]


def _zip_bytes(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        for name, payload in files.items():
            archive.writestr(name, payload)
    return buffer.getvalue()


def _manifest_bytes(series_uids: list[str]) -> bytes:
    lines = [
        'downloadServerUrl=https://example.invalid',
        'includeAnnotation=false',
        'manifestVersion=3.0',
        'ListOfSeriesToDownload=',
        *series_uids,
    ]
    return ('\n'.join(lines) + '\n').encode()


def test_validate_uid_rows_accepts_current_api_field_names():
    validate = _function('_validate_uid_rows')
    uids, rows = validate(
        [
            {'seriesInstanceUID': '1.2.3.4', 'collection': 'Prostate-3T'},
            {'SeriesInstanceUID': '1.2.3.5', 'Collection': 'PROSTATE-DIAGNOSIS'},
        ],
        expected=2,
        source='synthetic',
    )
    assert uids == ['1.2.3.4', '1.2.3.5']
    assert len(rows) == 2


def test_validate_uid_rows_rejects_duplicate_uid():
    validate = _function('_validate_uid_rows')
    with pytest.raises(RuntimeError, match='Duplicate SeriesInstanceUID'):
        validate(
            [{'SeriesInstanceUID': '1.2.3.4'}, {'SeriesInstanceUID': '1.2.3.4'}],
            expected=2,
            source='synthetic',
        )


def test_parse_tcia_series_uids_accepts_exact_manifest():
    parse = _function('parse_tcia_series_uids')
    uids = ['1.2.3.4', '1.2.3.5']
    assert parse(_manifest_bytes(uids), expected_series=2) == uids


def test_parse_tcia_series_uids_rejects_duplicate_uid():
    parse = _function('parse_tcia_series_uids')
    with pytest.raises(RuntimeError, match='duplicate SeriesInstanceUID'):
        parse(_manifest_bytes(['1.2.3.4', '1.2.3.4']), expected_series=2)


def test_validate_partition_uids_accepts_60_10_10_disjoint_sets():
    validate = _function('validate_partition_uids')
    uids = [f'1.2.840.{i}' for i in range(80)]
    validate(
        {
            'training': uids[:60],
            'leaderboard': uids[60:70],
            'test': uids[70:],
        }
    )


def test_validate_partition_uids_rejects_overlap():
    validate = _function('validate_partition_uids')
    uids = [f'1.2.840.{i}' for i in range(80)]
    leaderboard = [uids[0], *uids[60:69]]
    with pytest.raises(RuntimeError, match='overlap'):
        validate({'training': uids[:60], 'leaderboard': leaderboard, 'test': uids[70:]})


def test_source_key_for_patient_id_maps_both_official_prefixes():
    source_key_for_patient_id = _function('source_key_for_patient_id')
    assert source_key_for_patient_id('Prostate3T-01-0001') == 'prostate_3t'
    assert source_key_for_patient_id('ProstateDx-01-0001') == 'prostate_diagnosis'
    with pytest.raises(ValueError, match='exactly one source'):
        source_key_for_patient_id('Unknown-01-0001')


def test_enumerate_labels_hashes_members_and_preserves_partition_and_source():
    enumerate_labels = _function('enumerate_labels')
    archive = _zip_bytes(
        {
            'Leaderboard/Prostate3T-01-0001.nrrd': b'three-t',
            'Leaderboard/ProstateDx-01-0002.nrrd': b'diagnosis',
            'Leaderboard/README.txt': b'ignored',
        }
    )
    labels = enumerate_labels(archive, partition='leaderboard', expected_subjects=2)
    assert [record['patient_id'] for record in labels] == [
        'Prostate3T-01-0001',
        'ProstateDx-01-0002',
    ]
    assert [record['source_key'] for record in labels] == [
        'prostate_3t',
        'prostate_diagnosis',
    ]
    assert all(record['partition'] == 'leaderboard' for record in labels)
    assert all(len(record['sha256']) == 64 for record in labels)


def test_enumerate_labels_rejects_duplicate_patient():
    enumerate_labels = _function('enumerate_labels')
    archive = _zip_bytes(
        {
            'a/ProstateDx-01-0001.nrrd': b'a',
            'b/ProstateDx-01-0001.nrrd': b'b',
        }
    )
    with pytest.raises(RuntimeError, match='Duplicate NRRD PatientIDs'):
        enumerate_labels(archive, partition='training', expected_subjects=2)


def test_map_series_identity_preserves_partition_and_acquisition_fields():
    map_identity = _function('map_series_identity')
    partition_uids = {
        'training': ['1.2.3.4'],
        'leaderboard': ['1.2.3.5'],
        'test': ['1.2.3.6'],
    }
    rows: list[dict[str, Any]] = [
        {
            'PatientID': 'Prostate3T-01-0001',
            'collection_id': 'prostate_3t',
            'SeriesInstanceUID': '1.2.3.4',
            'Manufacturer': 'SIEMENS',
            'MagneticFieldStrength': 3.0,
        },
        {
            'PatientID': 'ProstateDx-01-0001',
            'collection_id': 'prostate_diagnosis',
            'SeriesInstanceUID': '1.2.3.5',
            'Manufacturer': 'Philips Medical Systems',
            'MagneticFieldStrength': 1.5,
        },
        {
            'PatientID': 'Prostate3T-01-0002',
            'collection_id': 'prostate_3t',
            'SeriesInstanceUID': '1.2.3.6',
            'Manufacturer': 'SIEMENS',
            'MagneticFieldStrength': 3.0,
        },
    ]
    result = map_identity(partition_uids, rows)
    records = {record['series_uid']: record for record in result['series_records']}
    assert records['1.2.3.4']['partition'] == 'training'
    assert records['1.2.3.5']['source_key'] == 'prostate_diagnosis'
    assert records['1.2.3.6']['series']['MagneticFieldStrength'] == 3.0


def test_validate_historical_conditions_requires_all_three_preserved_cases():
    validate = _function('validate_historical_conditions')
    label_index = {
        'ProstateDx-01-0006': {},
        'ProstateDx-01-0035': {},
        'ProstateDx-01-0055': {},
    }
    result = validate(label_index)
    assert result['missing'] == []
    assert result['prostate_dx_0006_present_in_current_official_training_archive'] is True


def test_validate_historical_conditions_reports_missing_case():
    validate = _function('validate_historical_conditions')
    result = validate({'ProstateDx-01-0006': {}, 'ProstateDx-01-0035': {}})
    assert result['missing'] == ['ProstateDx-01-0055']


def test_failure_record_keeps_result_bearing_boundary_closed():
    failure_record = _function('failure_record')
    result = failure_record(RuntimeError('synthetic failure'))
    assert result['status'] == 'failed'
    assert result['schema_version'] == 4
    assert result['authorization_boundary']['result_bearing_authorized'] is False
    assert result['authorization_boundary']['split_assignment_authorized'] is False
