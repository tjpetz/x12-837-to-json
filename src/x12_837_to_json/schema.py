"""Human-readable element names for the segments commonly found in an
X12 837 (Health Care Claim) transaction.

This is intentionally scoped to the segments used by the 837 Professional
(837P), Institutional (837I) and Dental (837D) implementation guides that
show up in day-to-day claims -- it is not a complete X12 data dictionary.
Any segment not listed here is still parsed and included in the output;
it just keeps numeric element keys (``element_01``, ``element_02``, ...)
instead of named ones, so nothing is ever silently dropped.
"""

from __future__ import annotations

from typing import Dict, List

# Segment ID -> ordered list of element names (element 01 first).
SEGMENT_ELEMENTS: Dict[str, List[str]] = {
    "ISA": [
        "authorization_information_qualifier",
        "authorization_information",
        "security_information_qualifier",
        "security_information",
        "sender_id_qualifier",
        "sender_id",
        "receiver_id_qualifier",
        "receiver_id",
        "interchange_date",
        "interchange_time",
        "repetition_separator",
        "interchange_control_version_number",
        "interchange_control_number",
        "acknowledgment_requested",
        "usage_indicator",
        "component_element_separator",
    ],
    "GS": [
        "functional_id_code",
        "sender_id",
        "receiver_id",
        "date",
        "time",
        "group_control_number",
        "responsible_agency_code",
        "version_release_industry_id",
    ],
    "ST": [
        "transaction_set_id_code",
        "transaction_set_control_number",
        "implementation_convention_reference",
    ],
    "BHT": [
        "hierarchical_structure_code",
        "transaction_set_purpose_code",
        "reference_id",
        "date",
        "time",
        "transaction_type_code",
    ],
    "HL": [
        "hierarchical_id_number",
        "hierarchical_parent_id_number",
        "hierarchical_level_code",
        "hierarchical_child_code",
    ],
    "PRV": [
        "provider_code",
        "reference_id_qualifier",
        "reference_id",
    ],
    "CUR": ["entity_identifier_code", "currency_code"],
    "NM1": [
        "entity_identifier_code",
        "entity_type_qualifier",
        "last_name_or_organization_name",
        "first_name",
        "middle_name",
        "name_prefix",
        "name_suffix",
        "id_code_qualifier",
        "id_code",
    ],
    "N3": ["address_line_1", "address_line_2"],
    "N4": ["city", "state", "postal_code", "country_code"],
    "PER": [
        "contact_function_code",
        "name",
        "comm_number_qualifier_1",
        "comm_number_1",
        "comm_number_qualifier_2",
        "comm_number_2",
        "comm_number_qualifier_3",
        "comm_number_3",
    ],
    "DMG": [
        "date_time_period_format_qualifier",
        "birth_date",
        "gender_code",
    ],
    "REF": [
        "reference_id_qualifier",
        "reference_id",
        "description",
    ],
    "SBR": [
        "payer_responsibility_sequence_code",
        "individual_relationship_code",
        "reference_id",
        "name",
        "insurance_type_code",
        "coordination_of_benefits_code",
        "condition_response_code",
        "employment_status_code",
        "claim_filing_indicator_code",
    ],
    "PAT": [
        "individual_relationship_code",
        "patient_location_code",
        "employment_status_code",
        "student_status_code",
        "date_of_death",
        "unit_basis_measurement_code",
        "weight",
        "pregnancy_indicator",
    ],
    "CLM": [
        "claim_submitter_id",
        "monetary_amount",
        "claim_filing_indicator_code_unused_1",
        "claim_filing_indicator_code_unused_2",
        "health_care_service_location",
        "provider_or_supplier_signature_indicator",
        "assignment_or_plan_participation_code",
        "benefits_assignment_certification_indicator",
        "release_of_information_code",
        "patient_signature_source_code",
        "related_causes_code",
        "special_program_code",
        "unused",
        "delay_reason_code",
    ],
    "DTP": ["date_time_qualifier", "date_time_period_format_qualifier", "date_time_period"],
    "CL1": [
        "admission_type_code",
        "admission_source_code",
        "patient_status_code",
    ],
    "AMT": ["amount_qualifier_code", "monetary_amount"],
    "K3": ["fixed_format_information"],
    "NTE": ["note_reference_code", "description"],
    "PWK": [
        "report_type_code",
        "report_transmission_code",
        "report_copies_needed",
        "entity_identifier_code",
        "id_code_qualifier",
        "id_code",
    ],
    "CN1": [
        "contract_type_code",
        "contract_amount",
        "contract_percentage",
        "contract_code",
        "terms_discount_percentage",
        "contract_version_id",
    ],
    "HI": None,  # handled specially -- repeating composite diagnosis/procedure codes
    "LX": ["assigned_number"],
    "SV1": [
        "procedure_code",
        "monetary_amount",
        "unit_or_basis_measurement_code",
        "quantity",
        "place_of_service_code",
        "service_type_code",
        "diagnosis_code_pointer",
        "monetary_amount_2",
        "emergency_indicator",
        "epsdt_indicator",
        "family_planning_indicator",
        "copay_status_code",
    ],
    "SV2": [
        "revenue_code",
        "procedure_code",
        "monetary_amount",
        "unit_or_basis_measurement_code",
        "quantity",
        "monetary_amount_2",
        "monetary_amount_3",
    ],
    "SV3": [
        "procedure_code",
        "monetary_amount",
        "facility_code",
        "quantity",
        "oral_cavity_designation",
    ],
    "TOO": ["code_list_qualifier_code", "tooth_code", "tooth_surface_code"],
    "CAS": None,  # repeating groups of (group_code, reason_code, amount, quantity)
    "CRC": [
        "code_category",
        "certification_condition_indicator",
        "condition_code_1",
        "condition_code_2",
        "condition_code_3",
        "condition_code_4",
        "condition_code_5",
    ],
    "HCP": [
        "pricing_methodology",
        "monetary_amount",
        "monetary_amount_2",
        "reference_id",
        "rate",
        "monetary_amount_3",
        "monetary_amount_4",
        "reject_reason_code",
        "policy_compliance_code",
        "exception_code",
    ],
    "QTY": ["quantity_qualifier", "quantity"],
    "SE": ["transaction_segment_count", "transaction_set_control_number"],
    "GE": ["number_of_transaction_sets_included", "group_control_number"],
    "IEA": ["number_of_included_functional_groups", "interchange_control_number"],
}


# Entity identifier codes (NM1-01 / N1-01) that matter for the 837.
ENTITY_IDENTIFIER_CODES = {
    "41": "submitter",
    "40": "receiver",
    "85": "billing_provider",
    "87": "pay_to_provider",
    "IL": "subscriber",
    "QC": "patient",
    "DN": "referring_provider",
    "P3": "primary_care_provider",
    "82": "rendering_provider",
    "77": "service_facility_location",
    "DQ": "supervising_provider",
    "PR": "payer",
    "QB": "purchased_service_provider",
    "45": "ambulance_pickup_location",
    "FA": "ambulance_dropoff_location",
}

# HL03 hierarchical level codes used by the 837.
HIERARCHICAL_LEVEL_CODES = {
    "20": "billing_provider",
    "22": "subscriber",
    "23": "patient",
}
