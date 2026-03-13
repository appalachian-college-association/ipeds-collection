# Updating IPEDS Access Database Files

## Current Status

All `.accdb` files in the project root are **final released versions** through FY2023-24.
The FY2024-25 file (`IPEDS202425.accdb`) is currently **provisional**.

NCES typically releases the final version of a provisional file approximately one year
after the original collection closed. Check [https://nces.ed.gov/ipeds/use-the-data/download-access-database](https://nces.ed.gov/ipeds/use-the-data/download-access-database)
for release announcements.

---

## When a Final File Is Published

### Step 1 — Rename the provisional file

In your project root, rename the current file to preserve it for comparison:

```
IPEDS202425.accdb  →  IPEDS202425_provisional.accdb
```

### Step 2 — Download and name the final file

Download the final `.accdb` from the NCES link above and save it to the project root as:

```
IPEDS202425_final.accdb
```

### Step 3 — Run the verification script

Open `bcla_verify_final.py` and update the two configuration lines near the top:

```python
SURVEY_YEAR = 2024
FINAL_ACCDB_PATH = "IPEDS202425_final.accdb"
```

Then run:

```
python bcla_verify_final.py
```

The script compares every BCLA institution value in `bcla_library.sqlite` against the
final `.accdb` and saves a timestamped Excel report to the project root.

### Step 4 — Review the report

- **No differences found:** Your posted reports are still accurate. Keep the Excel report
  on file as documentation.
- **Differences found:** Review the "All Changes" sheet. If any values affecting posted
  reports have changed, proceed to Step 5. If the changes are minor or affect
  non-reported variables, document your decision and stop here.

### Step 5 — Rebuild the database and reports (if needed)

If the verification report shows changes that affect your posted reports:

1. Rename the final file to the standard name the import script expects:
   ```
   IPEDS202425_final.accdb  →  IPEDS202425.accdb
   ```
2. Commit your current state to GitHub before rebuilding:
   ```
   git add .
   git commit -m "Pre-rebuild commit: replacing provisional FY2425 with final"
   git push
   ```
3. Re-run the full four-script pipeline in order:
   ```
   python bcla_library_import.py
   python bcla_variable_titles.py
   python bcla_report_generator.py
   python aca_fte_expenses_report.py
   ```
4. Spot-check output values against the IPEDS Data Center before sharing reports.
5. Update any posted reports and note the revision date.

### Step 6 — Clean up and commit

Once confirmed, delete or archive the provisional file:

```
IPEDS202425_provisional.accdb  →  (delete or move to an archive folder)
```

Commit the updated state:

```
git add .
git commit -m "Replace provisional FY2425 with final; reports updated"
git push
```

---

## File Naming Reference

| Academic Year | Provisional File | Final File (standard name) |
|---|---|---|
| 2019-20 | — | `IPEDS202021.accdb` |
| 2020-21 | — | `IPEDS202122.accdb` |
| 2021-22 | — | `IPEDS202223.accdb` |
| 2022-23 | — | `IPEDS202324.accdb` |
| 2023-24 | — | `IPEDS202425.accdb` ← currently provisional |
