import pytest

from x12_837_to_json.parser import X12ParseError, parse_x12


def test_detects_delimiters_from_isa():
    text = (
        "ISA*00*          *00*          *ZZ*SUBMITTERID    *ZZ*RECEIVERID     "
        "*190101*1253*^*00501*000000905*1*T*:~\n"
        "GS*HC*SUBMITTERID*RECEIVERID*20190101*1253*1*X*005010X222A1~\n"
        "IEA*1*000000905~\n"
    )
    envelope = parse_x12(text)
    assert envelope.delimiters.element == "*"
    assert envelope.delimiters.sub_element == ":"
    assert envelope.delimiters.segment == "~"
    assert envelope.delimiters.repetition == "^"


def test_isa_elements_are_not_split_on_component_separator():
    text = (
        "ISA*00*          *00*          *ZZ*SUBMITTERID    *ZZ*RECEIVERID     "
        "*190101*1253*^*00501*000000905*1*T*:~\n"
        "IEA*1*000000905~\n"
    )
    envelope = parse_x12(text)
    isa = envelope.segments[0]
    assert isa.id == "ISA"
    assert isa.element(16) == ":"


def test_splits_composite_elements_elsewhere():
    text = (
        "ISA*00*          *00*          *ZZ*SUBMITTERID    *ZZ*RECEIVERID     "
        "*190101*1253*^*00501*000000905*1*T*:~\n"
        "HI*ABK:Z0000*ABF:R109~\n"
        "IEA*1*000000905~\n"
    )
    envelope = parse_x12(text)
    hi = next(s for s in envelope.segments if s.id == "HI")
    assert hi.elements[0] == ["ABK", "Z0000"]
    assert hi.elements[1] == ["ABF", "R109"]


def test_tolerates_alternate_delimiters():
    text = "ISA|00|          |00|          |ZZ|SUBMITTERID    |ZZ|RECEIVERID     |190101|1253|^|00501|000000905|1|T|:\\\nGS|HC|SUBMITTERID|RECEIVERID|20190101|1253|1|X|005010X222A1\\\nIEA|1|000000905\\\n"
    envelope = parse_x12(text)
    assert envelope.delimiters.element == "|"
    assert envelope.delimiters.segment == "\\"
    gs = next(s for s in envelope.segments if s.id == "GS")
    assert gs.element(1) == "HC"


def test_rejects_non_x12_input():
    with pytest.raises(X12ParseError):
        parse_x12("this is not an X12 document")


def test_rejects_empty_input():
    with pytest.raises(X12ParseError):
        parse_x12("   \n  ")
