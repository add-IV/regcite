# 0001: Chunking by article, with paragraph packing

Status: accepted (M1)

## Decision

- Convert each regulation to Markdown with chapters and annexes as `#`, sections as `##`
  and articles as `###` (`ingest/convert.py`). `chunk_document` then gives every chunk a
  citation path such as `Chapter III > Section 2 > Article 14 Human oversight`.
- Within a section, pack paragraphs up to `max_chars=1200`; a single longer paragraph is
  kept whole.
- Use the consolidated texts, so citations point at wording that is in force, and pin each
  version in `data/manifest.json`.
- A plain line is a heading only if its number is not followed by `(`, so cross-reference
  cells such as `Article 1(1)` in the MDR/IVDR correlation tables are body text.

## Measured on the current corpus

- 1,828 chunks from 530 sections; median chunk 1,006 characters, longest 1,506.
- 331 of the 530 sections (62%) are split into more than one chunk.

## Consequences

- Several chunks of one article can fill the top-k slots. Retrieval metrics should be
  scored at article level (an article counts once) so that splitting does not distort
  recall@k; decide this before M4.
- Cross-references ("as referred to in Article 6") are not followed. Questions that need
  the referenced article rely on it also matching the query. Known limitation.
- The consolidated texts have no recitals, and tables are flattened to one paragraph per
  cell.
- Alternatives not tried: one chunk per whole article (very long for some articles) and
  overlapping windows. Revisit if article-level recall is poor.
