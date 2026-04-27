# Method Builder Loop

This project should not drift into random one-off county scraping. The product is a method for building county methods.

## North star

For each jurisdiction, produce a reusable source pack with evidence, not a heroic custom script.

## Loop

1. Discover candidate public sources.
2. Run a bounded sample only.
3. Score candidate authority and relevance.
4. Classify the table role.
5. Infer fields and joins with code.
6. Promote only strong candidates into `examples/sources/`.
7. Put weak or missing cases into a review queue.
8. Repeat the same loop on more states/counties.

## Guardrails

- Do not full-download before candidate authority is scored.
- Do not call a county covered just because ArcGIS returned something queryable.
- Do not build county-specific hacks unless they become reusable source-pack rules.
- Keep raw/sample records in `scratch/`, not git.
- Commit code, docs, source definitions, tests, schemas, and small synthetic fixtures.

## Promotion rule

A candidate can become a source-pack draft when it has:

- `authority.decision = promote_source_pack_candidate`
- a plausible countywide record count
- parcel ID mapped
- at least address/value/land-use/owner fields, or a clear role as base parcel geometry
- no unresolved derivative/stale/tiny-record warning

Anything else is not failure. It becomes a review item or an enrichment-search lead.
