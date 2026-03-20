"""
BCLA Airtable Export Script
============================
Generates a long-format CSV for importing into the Historical_IPEDS_Data
table in Airtable.

Long format means: one row per institution per year.
Example: 34 institutions x 6 years = up to 204 rows.

This is different from the wide-format reports (BCLA_Library_Combined_*.xlsx)
where all years are spread across columns. Long format works much better in
Airtable because you can filter by year, sort by any field, and add new years
by simply importing additional rows.

Run order: This script must be run AFTER:
  1. bcla_library_import.py  (creates bcla_library.sqlite)
  2. bcla_variable_titles.py (adds variable_titles table to the database)

Output file: BCLA_Airtable_Import_YYYYMMDD_HHMMSS.csv

Required packages: pandas, openpyxl
Install with: pip install pandas openpyxl --break-system-packages
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

# Path to the SQLite database (must match bcla_library_import.py)
DB_PATH = "bcla_library.sqlite"

# Years to include in the export.
YEARS = [2019, 2020, 2021, 2022, 2023, 2024]

# Value for the Data_Source field in Airtable.
# Must match exactly one of the single-select options in your Airtable base.
DATA_SOURCE = "IPEDS ACCDB"

# ============================================================================
# FIELD MAPPING
# ============================================================================
# This dictionary maps readable variable titles (from the variable_titles table
# in the database) to their exact Airtable field names.
#
# How this works:
#   - The SQLite database stores data using short IPEDS variable codes (like
#     LBOOKS, LEXPTOT). These are hard to read.
#   - The variable_titles table (created by bcla_variable_titles.py) maps each
#     code to a readable title like "Number of physical books".
#   - This dictionary then maps that readable title to the Airtable field name
#     (like AL_Physical_Books).
#
# If a variable title is NOT in this dictionary, it will be skipped.
# That is how we exclude the fields we don't want (gate questions, subtotals, etc.)

TITLE_TO_FIELD = {

    # ------------------------------------------------------------------
    # AL - Collections
    # ------------------------------------------------------------------
    'Number of physical books':
        'AL_Physical_Books',
    'Number of digital/electronic books':
        'AL_Electronic_Books',
    'Number of digital/electronic databases':
        'AL_Electronic_Databases',
    'Number of physical media':
        'AL_Physical_Media',
    'Number of digital/electronic media':
        'AL_Electronic_Media',
    'Number of physical serials':
        'AL_Physical_Serials',
    'Number of electronic serials':
        'AL_Electronic_Serials',
    'Total physical library collections (books, media and serials)':
        'AL_Total_Physical_Collections',
    'Total electronic library collections (books, databases, media and serials)':
        'AL_Total_Electronic_Collections',
    'Total library collections (physical and electronic)':
        'AL_Total_Collections',

    # ------------------------------------------------------------------
    # AL - Usage
    # ------------------------------------------------------------------
    'Total physical library circulations (books and media)':
        'AL_Physical_Circulations',
    'Total digital/electronic circulations (books and media)':
        'AL_Digital_Circulations',
    'Total library circulations (physical and digital/electronic)':
        'AL_Total_Circulations',
    'Total interlibrary loans and documents provided to other libraries':
        'AL_ILL_Provided',
    'Total interlibrary loans and documents received':
        'AL_ILL_Received',

    # ------------------------------------------------------------------
    # AL - Expenditures
    # ------------------------------------------------------------------
    'Total salaries and wages from the library budget':
        'AL_Salaries_Wages',
    'Total fringe benefits':
        'AL_Fringe_Benefits',
    'One-time purchases of books, serial backfiles, and other materials':
        'AL_Onetime_Purchases',
    'Ongoing commitments to subscriptions':
        'AL_Ongoing_Subscriptions',
    'Other materials/services expenditures':
        'AL_Other_Materials',
    'Total materials/services expenditures':
        'AL_Total_Materials',
    'Preservation services':
        'AL_Preservation',
    'Other operation and maintenance expenditures':
        'AL_Other_Operations',
    'Total operations and maintenance expenditures':
        'AL_Operations',
    'Total expenditures (salaries/wages, benefits, materials/services, and operations/maintenance)':
        'AL_Total_Expenditures',

    # ------------------------------------------------------------------
    # AL - Staff
    # Note: These fields were added to the AL survey starting in FY2020.
    # They will be blank for 2019 records. That is expected and correct.
    # ------------------------------------------------------------------
    'Total library FTE staff':
        'AL_Total_Staff_FTE',
    'Librarians FTE staff':
        'AL_Librarians_FTE',
    'Other professional FTE staff':
        'AL_Other_Professional_FTE',
    'All other paid FTE staff (Except Student Assistants)':
        'AL_Other_Paid_Staff_FTE',
    'Student assistants FTE':
        'AL_Student_Assistants_FTE',

    # ------------------------------------------------------------------
    # DRVAL - Derived / calculated fields
    # These are computed by NCES from the AL survey data above.
    # ------------------------------------------------------------------
    'Total library expenditures per FTE':
        'DRVAL_Expenditures_Per_FTE',
    'Salaries and wages from the library budget as a percent of total library expenditures':
        'DRVAL_Pct_Salaries',
    'Ongoing commitments to subscriptions as a percent of total library expenditures':
        'DRVAL_Pct_Subscriptions',
    'Physical books as a percent of the total library collection':
        'DRVAL_Pct_Physical_Books',
    'Digital/Electronic books as a percent of the total library collection':
        'DRVAL_Pct_Electronic_Books',
    'Digital/Electronic media as a percent of the total library collection':
        'DRVAL_Pct_Electronic_Media',
    'Digital/Electronic serials as a percent of the total library collection':
        'DRVAL_Pct_Electronic_Serials',
}

# The exact column order for the output CSV.
# These names must match your Airtable field names exactly.
# Skip: Record_ID (autonumber), Institution_Name (lookup), Import_Date (auto), Notes, Survey_Responses
AIRTABLE_COLUMNS = [
    'Institution',          # UNITID value — Airtable matches this to the Institutions table
    'IPEDS_Year',
    'Data_Source',
    'Total_Expenses',
    'DRVEF_FTE',
    'AL_Total_Expenditures',
    'AL_Salaries_Wages',
    'AL_Fringe_Benefits',
    'AL_Onetime_Purchases',
    'AL_Ongoing_Subscriptions',
    'AL_Other_Materials',
    'AL_Total_Materials',
    'AL_Preservation',
    'AL_Other_Operations',
    'AL_Operations',
    'AL_Physical_Books',
    'AL_Electronic_Books',
    'AL_Electronic_Databases',
    'AL_Physical_Media',
    'AL_Electronic_Media',
    'AL_Physical_Serials',
    'AL_Electronic_Serials',
    'AL_Total_Physical_Collections',
    'AL_Total_Electronic_Collections',
    'AL_Total_Collections',
    'AL_Physical_Circulations',
    'AL_Digital_Circulations',
    'AL_Total_Circulations',
    'AL_ILL_Received',
    'AL_ILL_Provided',
    'AL_Total_Staff_FTE',
    'AL_Librarians_FTE',
    'AL_Other_Professional_FTE',
    'AL_Other_Paid_Staff_FTE',
    'AL_Student_Assistants_FTE',
    'DRVAL_Expenditures_Per_FTE',
    'DRVAL_Pct_Salaries',
    'DRVAL_Pct_Subscriptions',
    'DRVAL_Pct_Physical_Books',
    'DRVAL_Pct_Electronic_Books',
    'DRVAL_Pct_Electronic_Media',
    'DRVAL_Pct_Electronic_Serials',
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_all_tables(conn):
    """Return a list of all table names in the database."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [row[0] for row in cursor.fetchall()]


def build_title_lookup(conn):
    """
    Build a dictionary mapping IPEDS variable codes to readable titles.

    Example: {'LBOOKS': 'Number of physical books', 'FTE': 'Full-time equivalent...'}

    This uses the variable_titles table created by bcla_variable_titles.py.
    If that table doesn't exist, returns an empty dict and prints a warning.
    """
    try:
        df = pd.read_sql_query(
            "SELECT varName, current_varTitle FROM variable_titles", conn
        )
        lookup = dict(zip(df['varName'], df['current_varTitle']))
        print(f"  Loaded {len(lookup)} variable title mappings from variable_titles table")
        return lookup
    except Exception as e:
        print(f"  WARNING: Could not load variable_titles table: {e}")
        print("  Please run bcla_variable_titles.py first, then re-run this script.")
        return {}


def get_institution_name_lookup(conn, all_tables):
    """
    Build a dictionary mapping UNITID -> Institution Name.
    Used only for sorting the output alphabetically.
    """
    hd_tables = sorted([t for t in all_tables if t.lower().startswith('hd')])
    if not hd_tables:
        print("  WARNING: No HD (directory) table found. Output will sort by UNITID.")
        return {}
    # Use the most recent HD table
    hd_table = hd_tables[-1]
    df = pd.read_sql_query(f"SELECT UNITID, INSTNM FROM {hd_table}", conn)
    return dict(zip(df['UNITID'], df['INSTNM']))


def get_finance_table_name(year):
    """
    Convert a survey year integer to the finance table name.

    IPEDS finance tables use overlapping two-digit years:
      2019 -> f1819_f2
      2020 -> f1920_f2
      2023 -> f2223_f2
    """
    prev_two = str(year - 1)[-2:]   # last 2 digits of previous year
    curr_two = str(year)[-2:]        # last 2 digits of current year
    return f"f{prev_two}{curr_two}_f2"


def extract_year_data(conn, year, title_lookup, all_tables):
    """
    Extract all data for one survey year.

    Returns a dictionary keyed by UNITID, where each value is a
    dictionary of {airtable_field_name: value}.

    Args:
        conn:         SQLite database connection
        year:         Integer survey year (e.g. 2019)
        title_lookup: Dict mapping varName -> readable title
        all_tables:   List of all table names in the database

    Returns:
        dict: {unitid: {field_name: value, ...}, ...}
    """
    data = {}  # Will hold {unitid: {field: value}} for this year

    # ---- FTE from DRVEF table ----------------------------------------
    # Table name example: drvef2019
    drvef_table = f"drvef{year}"
    if drvef_table in all_tables:
        df = pd.read_sql_query(f"SELECT UNITID, FTE FROM {drvef_table}", conn)
        for _, row in df.iterrows():
            uid = row['UNITID']
            if uid not in data:
                data[uid] = {}
            data[uid]['DRVEF_FTE'] = row['FTE']
        print(f"    {drvef_table}: {len(df)} rows")
    else:
        print(f"    NOTE: {drvef_table} not found — DRVEF_FTE will be blank for {year}")

    # ---- Total Expenses from Finance table ---------------------------
    # Table name example: f1819_f2 (for survey year 2019)
    fin_table = get_finance_table_name(year)
    if fin_table in all_tables:
        df = pd.read_sql_query(f"SELECT UNITID, F2E131 FROM {fin_table}", conn)
        for _, row in df.iterrows():
            uid = row['UNITID']
            if uid not in data:
                data[uid] = {}
            data[uid]['Total_Expenses'] = row['F2E131']
        print(f"    {fin_table}: {len(df)} rows")
    else:
        print(f"    NOTE: {fin_table} not found — Total_Expenses will be blank for {year}")

    # ---- AL and DRVAL tables -----------------------------------------
    # Both tables follow the same pattern: al2019, drval2019, al2020, etc.
    for table_prefix in ['al', 'drval']:
        table_name = f"{table_prefix}{year}"

        if table_name not in all_tables:
            print(f"    NOTE: {table_name} not found — {table_prefix.upper()} fields will be blank for {year}")
            continue

        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        matched_fields = 0

        for col in df.columns:
            if col == 'UNITID':
                continue  # Skip the ID column itself

            # Look up the readable title for this variable code
            # Example: 'LBOOKS' -> 'Number of physical books'
            title = title_lookup.get(col, '').strip()

            # Check if this title maps to an Airtable field we want
            airtable_field = TITLE_TO_FIELD.get(title)
            if airtable_field is None:
                continue  # This variable is not in our field list — skip it

            matched_fields += 1

            # Add this column's data for each institution
            for _, row in df.iterrows():
                uid = row['UNITID']
                if uid not in data:
                    data[uid] = {}
                data[uid][airtable_field] = row[col]

        print(f"    {table_name}: {len(df)} rows, {matched_fields} fields matched")

    return data


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("=" * 70)
    print("BCLA Airtable Export")
    print("=" * 70)
    print(f"Database: {DB_PATH}")
    print(f"Years:    {YEARS}")

    # Check that the database exists before doing anything else
    if not os.path.exists(DB_PATH):
        print(f"\nERROR: Database file '{DB_PATH}' not found.")
        print("Please run bcla_library_import.py first.")
        return

    # Open the database connection
    conn = sqlite3.connect(DB_PATH)

    print("\nLoading reference data...")
    all_tables = get_all_tables(conn)
    title_lookup = build_title_lookup(conn)
    inst_names = get_institution_name_lookup(conn, all_tables)

    print(f"  {len(all_tables)} tables found in database")
    print(f"  {len(inst_names)} institutions found")

    # Process each year and collect all rows
    all_rows = []

    for year in YEARS:
        print(f"\nProcessing year {year}...")

        year_data = extract_year_data(conn, year, title_lookup, all_tables)

        # Build one output row per institution for this year
        rows_added = 0
        for unitid, fields in year_data.items():
            row = {
                'Institution': unitid,   # UNITID — Airtable uses this to link to Institutions table
                'IPEDS_Year':  year,
                'Data_Source': DATA_SOURCE,
            }
            row.update(fields)
            all_rows.append(row)
            rows_added += 1

        print(f"  {rows_added} rows added for {year}")

    conn.close()

    if not all_rows:
        print("\nERROR: No data was collected. Check that the database has data.")
        return

    # Build a DataFrame from all rows
    df = pd.DataFrame(all_rows)

    # Add any missing Airtable columns as blank (None)
    # This ensures the CSV has all expected columns even if some data was missing
    for col in AIRTABLE_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Reorder columns to match Airtable exactly
    df = df[AIRTABLE_COLUMNS]

    # Sort alphabetically by institution name, then by year
    # This makes the imported data easier to browse in Airtable
    df['_sort_name'] = df['Institution'].map(
        lambda uid: inst_names.get(uid, str(uid))
    )
    df = df.sort_values(['_sort_name', 'IPEDS_Year']).reset_index(drop=True)
    df = df.drop(columns=['_sort_name'])

    # Save to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"BCLA_Airtable_Import_{timestamp}.csv"
    df.to_csv(filename, index=False)

    # Print summary
    print(f"\n{'=' * 70}")
    print("Export complete!")
    print(f"{'=' * 70}")
    print(f"Output file : {filename}")
    print(f"Total rows  : {len(df)}  ({len(df)} institution-year records)")
    print(f"Total fields: {len(df.columns)}")

    # Quick data availability summary
    print(f"\nRows per year:")
    for year in YEARS:
        count = len(df[df['IPEDS_Year'] == year])
        al_count = df[df['IPEDS_Year'] == year]['AL_Total_Expenditures'].notna().sum()
        print(f"  {year}: {count} rows  ({al_count} with AL data)")

    print(f"\nNext steps:")
    print(f"  1. Delete the 4 placeholder records in Historical_IPEDS_Data in Airtable")
    print(f"     (select all 4 rows, right-click, Delete records)")
    print(f"  2. In Airtable: Add or import → Import CSV → select {filename}")
    print(f"  3. On the field mapping screen, verify that 'Institution' maps to the")
    print(f"     Institution (linked) field — Airtable will match on UNITID")
    print(f"  4. Spot-check a few records against known values before sharing")


if __name__ == "__main__":
    main()
