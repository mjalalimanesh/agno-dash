# F1 Data Gotchas

Use these fixes when working with the sample F1 dataset.

## drivers_championship

- `position` is stored as TEXT.
- Use string comparisons:
  - Correct: `position = '1'`
  - Incorrect: `position = 1`

## constructors_championship

- `position` is stored as INTEGER.
- Use numeric comparisons:
  - Correct: `position = 1`
  - Incorrect: `position = '1'`

## race_wins

- `date` is stored as TEXT in `DD Mon YYYY` format.
- Parse with:
  - `TO_DATE(date, 'DD Mon YYYY')`
- Example for year filtering:
  - `EXTRACT(YEAR FROM TO_DATE(date, 'DD Mon YYYY')) = 2019`

## General Safety

- Keep SQL read-only (`SELECT` only).
- Add `LIMIT 50` by default unless a different limit is required.
- Use explicit columns instead of `SELECT *`.
