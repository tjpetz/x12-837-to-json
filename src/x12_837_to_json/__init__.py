"""x12_837_to_json

Parse an X12 EDI 837 (Health Care Claim: Professional / Institutional / Dental)
transaction and convert it into JSON.
"""

from .cli import convert
from .parser import X12Envelope, X12ParseError, X12Segment, parse_x12
from .transform import transform_document

__all__ = [
    "X12Envelope",
    "X12ParseError",
    "X12Segment",
    "convert",
    "parse_x12",
    "transform_document",
]

__version__ = "0.1.0"
