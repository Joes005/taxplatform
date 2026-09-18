# Sample import files

These CSVs exercise the Phase 3 import wizard (`/accounting/imports/new`) end to end. Each
file's header row is deliberately worded differently from the system's internal field names
(e.g. `"Customer Name"` vs `name`, `"HSN/SAC"` vs `hsn_sac`) — that's the point of the
column-mapping step: a source file never needs to match the system's field names exactly.

**Import order matters**, because later files reference records created by earlier ones by
name:

1. `sample_customers.csv`, `sample_vendors.csv`, `sample_products.csv`, `sample_ledgers.csv`
   — master data, any order, no dependencies
2. `sample_sales.csv` — references customer names from `sample_customers.csv`
3. `sample_purchases.csv` — references vendor names from `sample_vendors.csv`
4. `sample_payments.csv`, `sample_receipts.csv` — reference ledger names from
   `sample_ledgers.csv` (and `sample_receipts.csv` also references customer names)

Sales, purchases, payments, and receipts import types additionally require an existing
**financial year** on the company (create one first under Financial Years) whose date range
covers the rows' dates.

## Each file has one or two deliberately invalid rows

This is so the wizard's preview step has something real to show in the "errors" column —
they are not mistakes in the samples, they're the point:

| File | Invalid row | Why it fails |
|---|---|---|
| `sample_customers.csv` | `CUST-004` | Blank name — `name` is required |
| `sample_vendors.csv` | `VEND-004` | `NOTAVALIDGSTIN` fails the GSTIN structural check |
| `sample_products.csv` | `PRD-004` | `WIDGET` isn't `PRODUCT` or `SERVICE` |
| `sample_ledgers.csv` | `LDG-005` | `NOT_A_TYPE` isn't a valid `LedgerType` |
| `sample_sales.csv` | `INV-2026-004` | "Unknown Customer LLP" doesn't exist yet |
| `sample_purchases.csv` | `PB-2026-004` | `not-a-date` isn't a parseable date |
| `sample_payments.csv` | `PAY-2026-004` | "Nonexistent Ledger" doesn't exist yet |
| `sample_receipts.csv` | `RCPT-2026-004` | "Unknown Customer LLP" doesn't exist yet |

Committing any of these jobs creates records only for the rows that stayed `VALID` through
preview — the invalid row is skipped, never partially imported.

## Phase 4 — GST walkthrough (`sample_gst_*`, `sample_gstr2b.*`)

A second, self-contained set of files for exercising the GST compliance engine end to end.
All invoice dates fall in **April 2026**, so create a financial year covering that date
(e.g. `2026-27`, 01/04/2026–31/03/2027) before importing, and a GST return period for
April 2026 under **GST → New period**. The company's own GST profile can use any valid
GSTIN, e.g. `27AAPFT8890K1Z3` (Maharashtra).

Import order:

1. `sample_gst_customers.csv` (import type `CUSTOMERS`) and `sample_gst_vendors.csv`
   (`VENDORS`) — master data
2. `sample_gst_sales.csv` (`SALES`) — map the extra **Place of Supply State Code** column;
   this is what the GST engine actually classifies on (the free-text **Place of Supply**
   column is for humans only)
3. `sample_gst_purchases.csv` (`PURCHASES`) — map the extra **Supplier Invoice Number** /
   **Supplier Invoice Date** columns; GSTR-2B reconciliation matches on the *vendor's own*
   invoice numbering, not this company's internal one
4. `sample_gstr2b.csv`, `sample_gstr2b.xlsx`, or `sample_gstr2b.json` (import type `GSTR2B`,
   any one of the three — they describe the same four rows) — select the April 2026 return
   period when creating this import job

**After posting the sales and purchase invoices**, on the GST return period's page:

| Tab | What you'll see |
|---|---|
| GSTR-1 → B2B | Bangalore Buyers Pvt Ltd (inter-state) and Mumbai Retail Traders' `GINV-002` (intra-state) |
| GSTR-1 → B2C Large | `GINV-004` — ₹3,00,000 inter-state to an unregistered customer, over the ₹2.5L threshold |
| GSTR-1 → B2C Others | `GINV-003`, aggregated by state + rate |
| GSTR-1 → Validation | `GINV-005` flagged `MISSING_PLACE_OF_SUPPLY` / `REVIEW_REQUIRED` — it has no place of supply, so the engine refuses to guess |
| Reconciliation | Steelcore's `STL-9001` **MATCHED**; Northern Paper's `NPC-2201` **AMOUNT_MISMATCH** (books show ₹3,600 IGST, GSTR-2B shows ₹3,400); Bangalore Electricals' `BLR-771` **BOOKS_ONLY** (booked but not yet in GSTR-2B) and `BLR-999` **GSTR2B_ONLY** (in GSTR-2B but not yet booked) |
| GSTR-2B → import errors | The `NOTAVALIDGSTIN` row fails `INVALID_GSTIN_FORMAT` |
| ITC | Run reconciliation first, then review/approve the matched Steelcore result to see it flow into GSTR-3B's net liability |

`tests/test_gst_sample_data.py` in the backend imports these exact files through the real
pipeline and asserts these outcomes — if you ever edit a sample file, run that test to
confirm the numbers still line up.

## Phase 5 — TDS walkthrough (`sample_tds.csv`)

A file for exercising the TDS reconciliation import (`TDS → Transactions`, or via
`/accounting/imports/new` with import type `TDS`). Unlike the accounting/GST samples above,
the **deductees referenced in this file must already exist** before importing — TDS import
matches deductees by name but never creates one on the fly (PHASE5 section 3: no silent
guessing). Create these three under `TDS → Deductees` first:

| Name | PAN |
|---|---|
| Bright Consulting LLP | AAAPA1234A |
| Metro Freight Contractors | AABCM5678C |
| Skyline Properties | AACST9012D |

All dates fall in April 2026, so create a `2026-27` financial year (01/04/2026–31/03/2027)
and a `Q1` TDS return period before importing.

The fourth row (`Unknown Vendor LLP`) is deliberately invalid — that deductee is never
created, so the row fails `MISSING_DEDUCTEE` in the import preview rather than silently
creating a new deductee or being skipped without explanation.

Each imported row lands as a `DEDUCTED` `TDSTransaction` directly (this is reconciliation
import of already-known TDS data, not a calculation request — see PHASE5 section 29), ready
to allocate against a `TDSChallan` and reconcile.

## Phase 6 — Bank reconciliation walkthrough (`sample_bank_statement.csv`)

The exact scenario from the PHASE6 master prompt (section 54): four transactions on an
"HDFC Current Account" — a UPI receipt, an NEFT payment, a bank charge, and a second UPI
receipt. Import type `BANK_STATEMENT` via `Banking → Statements` (register the statement
first with matching opening/closing balances — ₹100,000 opening, ₹162,500 closing for this
file — then import its transactions from the statement's row).

To see **automatic matching** find a strong candidate, first create (under `Accounting`)
a Customer named "ABC Traders" and a Receipt against them dated 2026-09-01 for ₹50,000 with
reference `UPI900011` and vendor/customer likewise for "XYZ Suppliers" — a Payment dated
2026-09-02 for ₹12,000 with reference `NEFT700022`. Both share the bank account's own linked
Ledger as their `ledger_id` (link one when creating the bank account, or matching still works
without it — only the book-balance comparison needs it). Running `Run matching` on a
reconciliation session covering this period auto-matches both (exact amount + exact
reference + exact date clears the strong-match threshold); the ₹500 bank charge and the
second UPI receipt (no corresponding book entry in this walkthrough) are left `UNMATCHED` —
the bank charge is a natural candidate for `Create Adjustment`, the second receipt for manual
matching once its own Receipt exists.

`tests/test_bank_matching.py` in the backend exercises the same auto-match/ambiguous-match/
partial-match/adjustment scenarios programmatically — if you ever edit the matching engine's
scoring constants, run that suite to confirm the outcomes still line up.
