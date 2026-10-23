"""Turn a flat, tokenized X12 document into structured JSON for the 837
Health Care Claim transaction set (837P / 837I / 837D).

The 837 is built around a hierarchical loop structure (the ``HL``
segments): Billing Provider -> Subscriber -> Patient, with claims (the
2300 loop, starting at ``CLM``) and service lines (the 2400 loop,
starting at ``LX``) nested under the subscriber or patient level. This
module walks the flat segment list once and rebuilds that nesting.

Every segment is preserved somewhere in the output. Segments this module
doesn't have specific handling for are kept, named, under an
``other_segments`` list at whatever loop level they were found, so
nothing is silently dropped even if it isn't broken out into its own
field.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .parser import X12Envelope, X12Segment
from .schema import ENTITY_IDENTIFIER_CODES, HIERARCHICAL_LEVEL_CODES, SEGMENT_ELEMENTS

# Segments that can trail an NM1 and belong to that same "entity" (person
# or organization) rather than starting a new part of the loop.
_NM1_TRAILER_SEGMENTS = ("N3", "N4", "PER", "REF", "PRV")


def segment_to_dict(seg: X12Segment) -> dict:
    """Convert a single :class:`X12Segment` into a named JSON object,
    using the element names in ``schema.py`` when available.
    """

    if seg.id == "HI":
        return {"segment_id": "HI", "diagnosis_or_procedure_codes": _parse_hi(seg)}
    if seg.id == "CAS":
        return {"segment_id": "CAS", **_parse_cas(seg)}

    result: dict = {"segment_id": seg.id}
    names = SEGMENT_ELEMENTS.get(seg.id)
    if names:
        for position, name in enumerate(names, start=1):
            value = seg.element(position)
            if value is not None:
                result[name] = value
    else:
        for position, value in enumerate(seg.elements, start=1):
            if value not in (None, ""):
                result[f"element_{position:02d}"] = value
    return result


def _parse_hi(seg: X12Segment) -> List[dict]:
    codes = []
    for raw in seg.elements:
        parts = raw if isinstance(raw, list) else ([raw] if raw else [])
        parts = [p for p in parts]
        if not parts or not parts[0]:
            continue
        entry = {"qualifier": parts[0]}
        if len(parts) > 1 and parts[1] != "":
            entry["code"] = parts[1]
        if len(parts) > 2 and parts[2] != "":
            entry["date_or_flag"] = parts[2]
        codes.append(entry)
    return codes


def _parse_cas(seg: X12Segment) -> dict:
    elements = seg.elements
    group_code = elements[0] if elements else None
    adjustments = []
    i = 1
    while i < len(elements):
        chunk = elements[i : i + 3]
        if not any(chunk):
            break
        reason_code = chunk[0] if len(chunk) > 0 else None
        amount = chunk[1] if len(chunk) > 1 else None
        quantity = chunk[2] if len(chunk) > 2 else None
        entry = {}
        if reason_code:
            entry["reason_code"] = reason_code
        if amount:
            entry["amount"] = amount
        if quantity:
            entry["quantity"] = quantity
        if entry:
            adjustments.append(entry)
        i += 3
    return {"claim_adjustment_group_code": group_code, "adjustments": adjustments}


def _entity_key(seg: X12Segment) -> str:
    code = seg.element(1)
    return ENTITY_IDENTIFIER_CODES.get(code, f"entity_{code}")


def _consume_nm1_with_trailers(
    segments: List[X12Segment], index: int, extra_trailers: Tuple[str, ...] = ()
) -> Tuple[dict, int]:
    """Parse an NM1 segment at ``segments[index]`` plus any address/contact/
    reference segments that immediately follow it, returning the combined
    entity dict and the index of the next unconsumed segment.
    """

    trailers = _NM1_TRAILER_SEGMENTS + extra_trailers
    entity = segment_to_dict(segments[index])
    i = index + 1
    details = []
    n = len(segments)
    while i < n and segments[i].id in trailers:
        details.append(segment_to_dict(segments[i]))
        i += 1
    if details:
        entity["details"] = details
    return entity, i


def _add_entity(bucket: dict, key: str, entity: dict) -> None:
    if key in bucket:
        existing = bucket[key]
        if isinstance(existing, list):
            existing.append(entity)
        else:
            bucket[key] = [existing, entity]
    else:
        bucket[key] = entity


def _summarize_hl_segments(segments: List[X12Segment]) -> dict:
    """Fold the flat list of segments that belong to one HL loop (but
    before any claim) into a structured dict: entities (provider /
    subscriber / patient NM1 loops), SBR, PAT, DMG, PRV, DTP, etc.
    """

    result: dict = {}
    i = 0
    n = len(segments)
    while i < n:
        seg = segments[i]
        if seg.id == "NM1":
            entity, i = _consume_nm1_with_trailers(segments, i)
            _add_entity(result, _entity_key(seg), entity)
        elif seg.id == "SBR":
            result["subscriber_info"] = segment_to_dict(seg)
            i += 1
        elif seg.id == "PAT":
            result["patient_info"] = segment_to_dict(seg)
            i += 1
        elif seg.id == "DMG":
            result["demographic_info"] = segment_to_dict(seg)
            i += 1
        elif seg.id == "PRV":
            result.setdefault("provider_info", []).append(segment_to_dict(seg))
            i += 1
        elif seg.id == "CUR":
            result["currency"] = segment_to_dict(seg)
            i += 1
        elif seg.id == "DTP":
            result.setdefault("dates", []).append(segment_to_dict(seg))
            i += 1
        elif seg.id == "REF":
            result.setdefault("references", []).append(segment_to_dict(seg))
            i += 1
        else:
            result.setdefault("other_segments", []).append(segment_to_dict(seg))
            i += 1
    return result


def _build_service_line(segments: List[X12Segment], start: int) -> Tuple[dict, int]:
    """Parse the 2400 loop (service line): LX, then SV1/SV2/SV3, dates,
    diagnoses pointers, adjustments, etc., until the next LX, CLM or HL.
    """

    lx = segments[start]
    line: dict = {"line_number": segment_to_dict(lx).get("assigned_number")}
    i = start + 1
    n = len(segments)
    while i < n and segments[i].id not in ("LX", "CLM", "HL"):
        seg = segments[i]
        if seg.id in ("SV1", "SV2", "SV3"):
            line["service"] = segment_to_dict(seg)
            i += 1
        elif seg.id == "DTP":
            line.setdefault("dates", []).append(segment_to_dict(seg))
            i += 1
        elif seg.id == "HI":
            line.setdefault("procedure_or_condition_codes", []).extend(
                segment_to_dict(seg)["diagnosis_or_procedure_codes"]
            )
            i += 1
        elif seg.id == "REF":
            line.setdefault("references", []).append(segment_to_dict(seg))
            i += 1
        elif seg.id == "AMT":
            line.setdefault("amounts", []).append(segment_to_dict(seg))
            i += 1
        elif seg.id == "CAS":
            line.setdefault("claim_adjustments", []).append(segment_to_dict(seg))
            i += 1
        elif seg.id == "QTY":
            line.setdefault("quantities", []).append(segment_to_dict(seg))
            i += 1
        elif seg.id == "NTE":
            line.setdefault("notes", []).append(segment_to_dict(seg))
            i += 1
        elif seg.id == "NM1":
            entity, i = _consume_nm1_with_trailers(segments, i)
            _add_entity(line.setdefault("entities", {}), _entity_key(seg), entity)
            continue
        else:
            line.setdefault("other_segments", []).append(segment_to_dict(seg))
            i += 1
    return line, i


def _build_claim(segments: List[X12Segment], start: int) -> Tuple[dict, int]:
    """Parse the 2300 loop (claim): CLM, then diagnoses, dates,
    references, claim-level provider entities, and nested service lines,
    until the next CLM or HL.
    """

    clm = segments[start]
    claim: dict = {"claim_info": segment_to_dict(clm)}
    i = start + 1
    n = len(segments)
    service_lines: List[dict] = []
    while i < n and segments[i].id not in ("CLM", "HL"):
        seg = segments[i]
        if seg.id == "LX":
            line, i = _build_service_line(segments, i)
            service_lines.append(line)
        elif seg.id == "HI":
            claim.setdefault("diagnoses", []).extend(
                segment_to_dict(seg)["diagnosis_or_procedure_codes"]
            )
            i += 1
        elif seg.id == "DTP":
            claim.setdefault("dates", []).append(segment_to_dict(seg))
            i += 1
        elif seg.id == "REF":
            claim.setdefault("references", []).append(segment_to_dict(seg))
            i += 1
        elif seg.id == "NM1":
            entity, i = _consume_nm1_with_trailers(segments, i)
            _add_entity(claim.setdefault("entities", {}), _entity_key(seg), entity)
        else:
            claim.setdefault("other_segments", []).append(segment_to_dict(seg))
            i += 1
    if service_lines:
        claim["service_lines"] = service_lines
    return claim, i


def _build_hierarchical_loops(segments: List[X12Segment], start: int) -> Tuple[List[dict], int]:
    """Parse every ``HL`` segment loop in the transaction set and return
    the loops rebuilt into a parent/child tree, per HL01/HL02.
    """

    nodes: Dict[str, dict] = {}
    order: List[str] = []
    i = start
    n = len(segments)

    while i < n and segments[i].id == "HL":
        hl = segments[i]
        i += 1
        hl_id = hl.element(1)
        parent_id = hl.element(2)
        level_code = hl.element(3)

        loop_segments: List[X12Segment] = []
        while i < n and segments[i].id not in ("HL", "CLM"):
            loop_segments.append(segments[i])
            i += 1

        claims: List[dict] = []
        while i < n and segments[i].id == "CLM":
            claim, i = _build_claim(segments, i)
            claims.append(claim)

        node = {
            "hierarchical_id": hl_id,
            "parent_hierarchical_id": parent_id,
            "level_code": level_code,
            "level_type": HIERARCHICAL_LEVEL_CODES.get(level_code, level_code),
            "loop": _summarize_hl_segments(loop_segments),
            "children": [],
        }
        if claims:
            node["claims"] = claims

        nodes[hl_id] = node
        order.append(hl_id)

    roots: List[dict] = []
    for hl_id in order:
        node = nodes[hl_id]
        parent_id = node["parent_hierarchical_id"]
        if parent_id and parent_id in nodes:
            nodes[parent_id]["children"].append(node)
        else:
            roots.append(node)

    return roots, i


def _build_transaction_set(st: X12Segment, body: List[X12Segment], se: Optional[X12Segment]) -> dict:
    transaction: dict = {"header": segment_to_dict(st)}

    i = 0
    n = len(body)
    if i < n and body[i].id == "BHT":
        transaction["beginning_of_hierarchical_transaction"] = segment_to_dict(body[i])
        i += 1

    # Loops 1000A (submitter) / 1000B (receiver): NM1 segments that
    # appear before the first HL segment.
    while i < n and body[i].id != "HL":
        seg = body[i]
        if seg.id == "NM1":
            entity, i = _consume_nm1_with_trailers(body, i, extra_trailers=("PER",))
            key = _entity_key(seg)
            if key == "submitter":
                transaction["submitter"] = entity
            elif key == "receiver":
                transaction["receiver"] = entity
            else:
                _add_entity(transaction.setdefault("other_entities", {}), key, entity)
        else:
            transaction.setdefault("preamble_segments", []).append(segment_to_dict(seg))
            i += 1

    loops, i = _build_hierarchical_loops(body, i)
    transaction["hierarchical_loops"] = loops

    # Anything left over (e.g. LE/SE-adjacent segments outside the HL
    # structure) is kept rather than dropped.
    if i < n:
        transaction["trailing_segments"] = [segment_to_dict(s) for s in body[i:]]

    if se is not None:
        transaction["trailer"] = segment_to_dict(se)

    return transaction


def transform_document(envelope: X12Envelope) -> dict:
    """Turn a tokenized :class:`X12Envelope` into the full nested JSON
    document: interchange(s) -> functional group(s) -> transaction
    set(s), with each 837 transaction set's HL hierarchy, claims and
    service lines rebuilt.
    """

    segments = envelope.segments
    n = len(segments)
    i = 0
    document: dict = {
        "delimiters": envelope.delimiters.to_dict(),
        "interchanges": [],
    }

    while i < n and segments[i].id == "ISA":
        isa = segments[i]
        i += 1
        interchange: dict = {
            "header": segment_to_dict(isa),
            "functional_groups": [],
        }

        while i < n and segments[i].id == "GS":
            gs = segments[i]
            i += 1
            functional_group: dict = {
                "header": segment_to_dict(gs),
                "transaction_sets": [],
            }

            while i < n and segments[i].id == "ST":
                st = segments[i]
                i += 1
                body_start = i
                while i < n and segments[i].id != "SE":
                    i += 1
                body = segments[body_start:i]
                se = segments[i] if i < n and segments[i].id == "SE" else None
                if se is not None:
                    i += 1
                functional_group["transaction_sets"].append(
                    _build_transaction_set(st, body, se)
                )

            if i < n and segments[i].id == "GE":
                functional_group["trailer"] = segment_to_dict(segments[i])
                i += 1

            interchange["functional_groups"].append(functional_group)

        if i < n and segments[i].id == "IEA":
            interchange["trailer"] = segment_to_dict(segments[i])
            i += 1

        document["interchanges"].append(interchange)

    if i < n:
        document["unconsumed_segments"] = [s.to_dict() for s in segments[i:]]

    return document
