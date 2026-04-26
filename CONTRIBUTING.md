# Contributing

County Parcel Data Toolkit welcomes source definitions, adapters, tests, and documentation.

Do not contribute downloaded parcel/person records. Source definitions and field mappings are fine; raw data exports are not.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest -q
```

## Good source contributions

- public source URL
- source type
- field mapping to normalized fields
- notes on access limits or terms
- no bundled records
