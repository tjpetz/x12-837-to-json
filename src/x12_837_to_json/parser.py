"""Low-level X12 tokenizer.

This module is deliberately generic: it knows nothing about the 837
transaction set specifically. It is responsible for:

1. Detecting the delimiters a document uses (element, sub-element /
   component, repetition, and segment terminator) from the ISA header,
   per the X12 standard, which fixes the ISA segment to exactly 106
   characters before the segment terminator.
2. Splitting the raw document into segments, and each segment into
   elements (and composite elements into components).

The result is a flat list of :class:`X12Segment` objects that later
stages (see ``transform.py``) turn into the nested 837 JSON structure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Union

ElementValue = Union[str, List[str]]


class X12ParseError(ValueError):
    """Raised when the input does not look like a valid X12 document."""


@dataclass
class X12Segment:
    """A single X12 segment, e.g. ``NM1*IL*1*DOE*JOHN****MI*123456789``."""

    id: str
    elements: List[ElementValue] = field(default_factory=list)

    def element(self, index: int, default=None):
        """Return element ``index`` (1-based, matching the X12 numbering
        where element 01 is ``elements[0]``). Returns ``default`` if the
        element is absent or empty.
        """
        i = index - 1
        if i < 0 or i >= len(self.elements):
            return default
        value = self.elements[i]
        if value == "" or value is None:
            return default
        return value

    def to_dict(self) -> dict:
        return {"id": self.id, "elements": self.elements}


@dataclass
class X12Delimiters:
    element: str
    sub_element: str
    segment: str
    repetition: str = "^"

    def to_dict(self) -> dict:
        return {
            "element_separator": self.element,
            "component_separator": self.sub_element,
            "repetition_separator": self.repetition,
            "segment_terminator": self.segment,
        }


@dataclass
class X12Envelope:
    """The full result of tokenizing an X12 document."""

    delimiters: X12Delimiters
    segments: List[X12Segment]


def _detect_delimiters(raw: str) -> X12Delimiters:
    if len(raw) < 106 or not raw.startswith("ISA"):
        raise X12ParseError(
            "Input does not start with a 106-character ISA segment; "
            "this does not look like a valid X12 document."
        )

    element_sep = raw[3]
    sub_element_sep = raw[104]
    segment_terminator = raw[105]

    # ISA11 (repetition separator in 5010) sits right before ISA12.
    # Positions are fixed regardless of delimiter choice.
    isa_fields = raw[:105].split(element_sep)
    repetition_sep = isa_fields[11] if len(isa_fields) > 11 else "^"
    if not repetition_sep or len(repetition_sep) != 1:
        repetition_sep = "^"

    return X12Delimiters(
        element=element_sep,
        sub_element=sub_element_sep,
        segment=segment_terminator,
        repetition=repetition_sep,
    )


def _split_element(raw_element: str, sub_element_sep: str) -> ElementValue:
    if sub_element_sep and sub_element_sep in raw_element:
        return raw_element.split(sub_element_sep)
    return raw_element


def parse_x12(text: str) -> X12Envelope:
    """Tokenize a raw X12 document into an :class:`X12Envelope`.

    Accepts documents that use any delimiters (they are auto-detected
    from the ISA segment), and tolerates the cosmetic line breaks/
    whitespace that some trading partners insert after each segment
    terminator for readability.
    """

    raw = text.strip("﻿")  # tolerate a BOM
    if not raw.strip():
        raise X12ParseError("Input is empty.")

    # Trim leading whitespace only; ISA must start at position 0.
    raw = raw.lstrip("\n\r\t ")

    delimiters = _detect_delimiters(raw)

    raw_segments = raw.split(delimiters.segment)
    segments: List[X12Segment] = []
    for raw_segment in raw_segments:
        cleaned = raw_segment.strip("\r\n \t")
        if not cleaned:
            continue
        raw_elements = cleaned.split(delimiters.element)
        segment_id = raw_elements[0].strip()
        if segment_id == "ISA":
            # ISA never contains composite elements -- ISA16 is simply the
            # component separator character itself, which would otherwise
            # be (mis)split against itself.
            elements: List[ElementValue] = list(raw_elements[1:])
        else:
            elements = [
                _split_element(e, delimiters.sub_element) for e in raw_elements[1:]
            ]
        segments.append(X12Segment(id=segment_id, elements=elements))

    if not segments:
        raise X12ParseError("No segments were found in the input.")

    return X12Envelope(delimiters=delimiters, segments=segments)
