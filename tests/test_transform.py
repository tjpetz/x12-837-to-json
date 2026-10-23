import json
from pathlib import Path

import pytest

from x12_837_to_json.cli import convert

SAMPLE_PATH = Path(__file__).parent / "sample_data" / "sample_837p.edi"


@pytest.fixture(scope="module")
def sample_json():
    text = SAMPLE_PATH.read_text()
    return convert(text)


def _find_transaction(document):
    return document["interchanges"][0]["functional_groups"][0]["transaction_sets"][0]


def test_envelope_headers(sample_json):
    interchange = sample_json["interchanges"][0]
    assert interchange["header"]["interchange_control_number"] == "000000905"
    assert interchange["trailer"]["interchange_control_number"] == "000000905"

    fg = interchange["functional_groups"][0]
    assert fg["header"]["functional_id_code"] == "HC"


def test_transaction_header_and_bht(sample_json):
    transaction = _find_transaction(sample_json)
    assert transaction["header"]["transaction_set_id_code"] == "837"
    assert transaction["beginning_of_hierarchical_transaction"]["hierarchical_structure_code"] == "0019"


def test_submitter_and_receiver(sample_json):
    transaction = _find_transaction(sample_json)
    assert transaction["submitter"]["last_name_or_organization_name"] == "SUBMITTER NAME"
    assert transaction["submitter"]["details"][0]["name"] == "CONTACT NAME"
    assert transaction["receiver"]["last_name_or_organization_name"] == "RECEIVER NAME"


def test_billing_provider_loop(sample_json):
    transaction = _find_transaction(sample_json)
    billing_loop = transaction["hierarchical_loops"][0]
    assert billing_loop["level_type"] == "billing_provider"
    provider = billing_loop["loop"]["billing_provider"]
    assert provider["last_name_or_organization_name"] == "BILLING PROVIDER NAME"
    assert provider["details"][0]["address_line_1"] == "123 MAIN ST"
    assert provider["details"][1]["city"] == "ANYTOWN"


def test_subscriber_loop_and_claim(sample_json):
    transaction = _find_transaction(sample_json)
    billing_loop = transaction["hierarchical_loops"][0]
    subscriber_loop = billing_loop["children"][0]

    assert subscriber_loop["level_type"] == "subscriber"
    subscriber = subscriber_loop["loop"]["subscriber"]
    assert subscriber["last_name_or_organization_name"] == "DOE"
    assert subscriber["first_name"] == "JOHN"
    assert subscriber_loop["loop"]["demographic_info"]["birth_date"] == "19700101"

    claims = subscriber_loop["claims"]
    assert len(claims) == 1
    claim = claims[0]
    assert claim["claim_info"]["claim_submitter_id"] == "PATIENT_ACCT_1"
    assert claim["claim_info"]["monetary_amount"] == "150"
    assert claim["diagnoses"] == [{"qualifier": "ABK", "code": "Z0000"}]
    assert claim["entities"]["rendering_provider"]["last_name_or_organization_name"] == "SMITH"


def test_service_lines(sample_json):
    transaction = _find_transaction(sample_json)
    billing_loop = transaction["hierarchical_loops"][0]
    subscriber_loop = billing_loop["children"][0]
    claim = subscriber_loop["claims"][0]

    lines = claim["service_lines"]
    assert len(lines) == 2
    assert lines[0]["line_number"] == "1"
    assert lines[0]["service"]["procedure_code"] == ["HC", "99213"]
    assert lines[0]["service"]["monetary_amount"] == "100"
    assert lines[0]["dates"][0]["date_time_period"] == "20190101"

    assert lines[1]["line_number"] == "2"
    assert lines[1]["service"]["procedure_code"] == ["HC", "85025"]


def test_output_is_json_serializable(sample_json):
    # Should not raise -- everything in the tree must be JSON-safe.
    json.dumps(sample_json)


def test_no_unconsumed_segments(sample_json):
    assert "unconsumed_segments" not in sample_json
    transaction = _find_transaction(sample_json)
    assert "trailing_segments" not in transaction
