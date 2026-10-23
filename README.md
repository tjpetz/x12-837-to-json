# x12-837-to-json

Parse an X12 EDI 837 (Health Care Claim: Professional / Institutional /
Dental) transaction and convert it into JSON.

The library is a two-stage pipeline:

1. **Tokenizer** (`x12_837_to_json.parser`) — a generic X12 tokenizer.
   It auto-detects the element, component and segment delimiters from
   the `ISA` header (per the X12 standard) and splits the raw document
   into a flat list of segments/elements. This part knows nothing about
   the 837 specifically, so it also works as a general-purpose X12
   tokenizer.
2. **Transformer** (`x12_837_to_json.transform`) — walks the flat
   segment list and rebuilds the 837's hierarchical structure:
   interchange -> functional group -> transaction set -> `HL` loops
   (billing provider -> subscriber -> patient) -> claims (`CLM`, loop
   2300) -> service lines (`LX`/`SV1`/`SV2`, loop 2400).

Every segment is preserved in the output somewhere. Segments this
project doesn't have a named field for are still included, under an
`other_segments` list at whatever loop they were found in, so nothing is
silently dropped even when a schema isn't defined for it.

## Scope / limitations

This targets the segments most commonly seen in everyday 837P/837I/837D
claims (submitter/receiver, billing provider, subscriber, patient,
payer, claim-level diagnoses and references, and service lines). It is
**not** a full implementation of the 837 5010 implementation guides —
some less common loops and segments will come through as generic
`other_segments` entries (with all their data intact, just not broken
out into named sub-fields) rather than fully modeled structures. Treat
it as a strong starting point rather than a certified translator.

## Install

Requires Python 3.9+. No third-party runtime dependencies.

If your `python3`/`pip3` come from Homebrew, Homebrew marks that
Python installation "externally managed" (PEP 668), so a plain
`pip install` is blocked with an `externally-managed-environment`
error. Use a virtual environment instead — this is the standard,
Homebrew-recommended way to install Python packages:

```bash
# from the project directory
python3 -m venv .venv
source .venv/bin/activate      # on fish: source .venv/bin/activate.fish
pip install -e .
```

The `x12-837-to-json` command and the `x12_837_to_json` module are then
available whenever that virtual environment is active. Deactivate with
`deactivate`, and reactivate later with the same `source .venv/bin/activate`
command — no need to reinstall.

If you'd rather not think about activating a venv each time, `pipx`
(itself installable via `brew install pipx`) installs the CLI into its
own isolated environment and puts it on your `PATH` globally:

```bash
brew install pipx
pipx install .
```

(Use `pipx install -e .` instead if you're actively editing the code and
want the installed command to pick up changes immediately.) `pipx` is
for the CLI only — if you also want to `import x12_837_to_json` from
your own scripts, use the venv approach above.

## Usage

### Command line

```bash
# File in, file out
x12-837-to-json claim.837 -o claim.json

# Or use stdin/stdout
cat claim.837 | x12-837-to-json > claim.json

# Compact output
x12-837-to-json claim.837 --indent 0
```

### Python

```python
from x12_837_to_json import convert

with open("claim.837") as f:
    text = f.read()

data = convert(text)  # a plain dict, ready for json.dump / json.dumps
```

If you need lower-level access:

```python
from x12_837_to_json import parse_x12, transform_document

envelope = parse_x12(text)      # flat list of X12Segment (delimiters auto-detected)
document = transform_document(envelope)  # nested JSON-ready dict
```

## Output shape

```jsonc
{
  "delimiters": { "element_separator": "*", "component_separator": ":", "segment_terminator": "~", "repetition_separator": "^" },
  "interchanges": [
    {
      "header": { "segment_id": "ISA", "...": "..." },
      "functional_groups": [
        {
          "header": { "segment_id": "GS", "...": "..." },
          "transaction_sets": [
            {
              "header": { "segment_id": "ST", "transaction_set_id_code": "837", "..." : "..." },
              "beginning_of_hierarchical_transaction": { "...": "..." },
              "submitter": { "...": "..." },
              "receiver": { "...": "..." },
              "hierarchical_loops": [
                {
                  "hierarchical_id": "1",
                  "level_type": "billing_provider",
                  "loop": { "billing_provider": { "...": "..." } },
                  "children": [
                    {
                      "hierarchical_id": "2",
                      "level_type": "subscriber",
                      "loop": { "subscriber": { "...": "..." }, "subscriber_info": { "...": "..." } },
                      "claims": [
                        {
                          "claim_info": { "segment_id": "CLM", "claim_submitter_id": "...", "monetary_amount": "..." },
                          "diagnoses": [{ "qualifier": "ABK", "code": "Z0000" }],
                          "entities": { "rendering_provider": { "...": "..." } },
                          "service_lines": [
                            { "line_number": "1", "service": { "...": "..." }, "dates": [{ "...": "..." }] }
                          ]
                        }
                      ],
                      "children": []
                    }
                  ]
                }
              ],
              "trailer": { "segment_id": "SE", "...": "..." }
            }
          ],
          "trailer": { "segment_id": "GE", "...": "..." }
        }
      ],
      "trailer": { "segment_id": "IEA", "...": "..." }
    }
  ]
}
```

## Development

Same externally-managed-environment caveat applies here — use the venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

`tests/sample_data/sample_837p.edi` is a small, hand-built 837P sample
(one billing provider, one subscriber, one claim with two service
lines) used by the test suite.
