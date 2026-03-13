"""
BCLA Data Verification Script
Compares values in bcla_library.sqlite (built from provisional IPEDS data)
against the finalized IPEDS .accdb file for the same year.

Use this script after NCES releases a final .accdb to check whether any
BCLA institution values changed, so you know if posted reports need updating.

How to use:
  1. Rename your current provisional .accdb file:
       IPEDS202324.accdb → IPEDS202324_provisional.accdb
  2. Download the final .accdb and name it:
       IPEDS202324_final.accdb
  3. Update SURVEY_YEAR and FINAL_ACCDB_PATH below
  4. Run: python bcla_verify_final.py

Required packages: pandas, pyodbc, openpyxl
Install with: pip install pandas pyodbc openpyxl --break-system-packages
"""

import sqlite3
import pandas as pd
import pyodbc
import os
from datetime import datetime

# ============================================================================
# CONFIGURATION — Update these values before running
# ============================================================================

# The IPEDS survey year you are verifying (end year of academic year)
# Example: 2023 = the 2022-23 academic year
SURVEY_YEAR = 2023

# Path to the FINAL (not provisional) .accdb file
FINAL_ACCDB_PATH = "IPEDS202324_final.accdb"

# Your SQLite database built from the provisional data
DB_PATH = "bcla_library.sqlite"

# BCLA institution Unit IDs (same list as bcla_library_import.py)
BCLA_UNITIDS = [
    156189,  # Alice Lloyd College
    156295,  # Berea College
    237181,  # Bethany College
    231554,  # Bluefield University
    198066,  # Brevard College
    219790,  # Bryan College-Dayton
    156365,  # Campbellsville University
    219806,  # Carson-Newman University
    237358,  # Davis & Elkins College
    232025,  # Emory & Henry University
    232089,  # Ferrum College
    220473,  # Johnson University
    132879,  # Johnson University Florida
    157100,  # Kentucky Christian University
    220516,  # King University
    220613,  # Lee University
    198808,  # Lees-McRae College
    198835,  # Lenoir-Rhyne University
    220631,  # Lincoln Memorial University
    157216,  # Lindsey Wilson College
    198899,  # Mars Hill University
    220710,  # Maryville College
    486901,  # Milligan University
    199032,  # Montreat College
    221731,  # Tennessee Wesleyan University
    221519,  # The University of the South
    221953,  # Tusculum University
    157863,  # Union College
    237312,  # University of Charleston
    157535,  # University of Pikeville
    199865,  # Warren Wilson College
    237969,  # West Virginia Wesleyan College
    238078,  # Wheeling University
    141361,  # Young Harris College
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def build_table_names(year):
    """
    Build the expected table names for a given survey year.
    These must match what bcla_library_import.py wrote into SQLite.

    Args:
        year (int): Survey year (e.g., 2023)

    Returns:
        dict: Mapping of table type to table name
    """
    prev_year = str(year - 1)
    year_str = str(year)

    return {
        'al':    f"AL{year_str}",
        'drvef': f"DRVEF{year_str}",
        'drval': f"DRVAL{year_str}",
        'f':     f"F{prev_year[-2:]}{year_str[-2:]}_F2",
    }


def connect_to_accdb(accdb_path):
    """
    Connect to a Microsoft Access .accdb file using pyodbc.

    Args:
        accdb_path (str): Full or relative path to the .accdb file

    Returns:
        pyodbc.Connection or None: Connection object, or None if it failed
    """
    # os.path.abspath converts a relative path to a full path,
    # which the Access driver requires
    abs_path = os.path.abspath(accdb_path)

    conn_str = (
        r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
        f'DBQ={abs_path};'
    )

    try:
        conn = pyodbc.connect(conn_str)
        print(f"  ✓ Connected to {os.path.basename(accdb_path)}")
        return conn
    except Exception as e:
        print(f"  ✗ Could not connect to {accdb_path}")
        print(f"    Error: {e}")
        return None


def get_accdb_tables(accdb_conn):
    """
    Get a list of all table names in the Access database.

    Args:
        accdb_conn: pyodbc connection to the .accdb file

    Returns:
        list: Table names (uppercase)
    """
    cursor = accdb_conn.cursor()
    tables = [row.table_name for row in cursor.tables(tableType='TABLE')]
    return [t.upper() for t in tables]


def read_from_accdb(accdb_conn, table_name, unitids):
    """
    Read a table from the Access database, filtered to BCLA institutions.

    Args:
        accdb_conn: pyodbc connection
        table_name (str): Table to read (e.g., 'AL2023')
        unitids (list): List of UNITID integers to filter to

    Returns:
        pandas.DataFrame or None: The filtered data, or None if table not found
    """
    # Check if the table exists (case-insensitive)
    available = get_accdb_tables(accdb_conn)
    if table_name.upper() not in available:
        print(f"  ⚠  Table {table_name} not found in final .accdb")
        print(f"     Available tables (sample): {available[:10]}")
        return None

    try:
        query = f"SELECT * FROM [{table_name}]"
        df = pd.read_sql(query, accdb_conn)

        # Filter to BCLA institutions
        if 'UNITID' in df.columns:
            df = df[df['UNITID'].isin(unitids)].copy()
            df = df.reset_index(drop=True)

        return df

    except Exception as e:
        print(f"  ✗ Error reading {table_name}: {e}")
        return None


def read_from_sqlite(sqlite_conn, table_name):
    """
    Read a table from the SQLite database.

    Args:
        sqlite_conn: sqlite3 connection
        table_name (str): Table to read (lowercase, as stored in SQLite)

    Returns:
        pandas.DataFrame or None
    """
    # SQLite stores table names in the case they were written;
    # bcla_library_import.py lowercases them (e.g., 'al2023')
    sqlite_table = table_name.lower()

    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing = [row[0].lower() for row in cursor.fetchall()]

    if sqlite_table not in existing:
        print(f"  ⚠  Table '{sqlite_table}' not found in SQLite database")
        return None

    try:
        df = pd.read_sql_query(f"SELECT * FROM {sqlite_table}", sqlite_conn)
        return df
    except Exception as e:
        print(f"  ✗ Error reading {sqlite_table} from SQLite: {e}")
        return None


def get_institution_names(sqlite_conn):
    """
    Get a UNITID → Institution Name mapping from the SQLite hd table.

    Args:
        sqlite_conn: sqlite3 connection

    Returns:
        dict: {unitid: institution_name}
    """
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    # Find any hd table (e.g., hd2023, hd2019)
    hd_tables = sorted([t for t in tables if t.lower().startswith('hd')])

    if not hd_tables:
        return {}

    # Use the most recent hd table
    hd_table = hd_tables[-1]

    try:
        df = pd.read_sql_query(f"SELECT UNITID, INSTNM FROM {hd_table}", sqlite_conn)
        return dict(zip(df['UNITID'], df['INSTNM']))
    except Exception:
        return {}


# ============================================================================
# COMPARISON LOGIC
# ============================================================================

def compare_table(table_name, final_df, sqlite_df, inst_names):
    """
    Compare two DataFrames (final vs. provisional) and find differences.

    Both DataFrames should contain the same BCLA institutions.
    Returns a list of difference records for reporting.

    Args:
        table_name (str): Name of the table being compared
        final_df (DataFrame): Data from the final .accdb file
        sqlite_df (DataFrame): Data from the SQLite database (provisional)
        inst_names (dict): {unitid: name} for readable output

    Returns:
        list: List of dicts, one per changed value
    """
    differences = []

    if final_df is None or sqlite_df is None:
        return differences

    # Standardize column names to uppercase for comparison
    final_df.columns = [c.upper() for c in final_df.columns]
    sqlite_df.columns = [c.upper() for c in sqlite_df.columns]

    # Find columns that exist in both DataFrames (excluding UNITID)
    final_cols = set(final_df.columns)
    sqlite_cols = set(sqlite_df.columns)
    shared_cols = (final_cols & sqlite_cols) - {'UNITID'}

    # Columns that only appear in one source — note but don't compare
    only_in_final = final_cols - sqlite_cols - {'UNITID'}
    only_in_sqlite = sqlite_cols - final_cols - {'UNITID'}

    if only_in_final:
        print(f"  ℹ  New columns in final (not in SQLite): {sorted(only_in_final)}")
    if only_in_sqlite:
        print(f"  ℹ  Columns in SQLite not in final: {sorted(only_in_sqlite)}")

    # Compare row by row, institution by institution
    for unitid in BCLA_UNITIDS:
        final_row = final_df[final_df['UNITID'] == unitid]
        sqlite_row = sqlite_df[sqlite_df['UNITID'] == unitid]

        # Skip if institution not present in either source
        if final_row.empty and sqlite_row.empty:
            continue

        # Note if institution is missing from one source
        if final_row.empty:
            differences.append({
                'Table': table_name,
                'UNITID': unitid,
                'Institution': inst_names.get(unitid, f"Unknown ({unitid})"),
                'Variable': '— ALL —',
                'Provisional Value': '(data present)',
                'Final Value': '(institution missing from final)',
                'Change Type': 'Institution removed'
            })
            continue

        if sqlite_row.empty:
            differences.append({
                'Table': table_name,
                'UNITID': unitid,
                'Institution': inst_names.get(unitid, f"Unknown ({unitid})"),
                'Variable': '— ALL —',
                'Provisional Value': '(institution missing from provisional)',
                'Final Value': '(data present)',
                'Change Type': 'Institution added'
            })
            continue

        # Compare each shared column
        for col in sorted(shared_cols):
            final_val = final_row.iloc[0][col]
            sqlite_val = sqlite_row.iloc[0][col]

            # Treat NaN/None as equivalent to avoid false positives
            # pd.isna() returns True for None, float('nan'), and pd.NaT
            both_null = pd.isna(final_val) and pd.isna(sqlite_val)
            if both_null:
                continue

            # Compare values — convert to string for consistent comparison
            # across different numeric types (int vs float)
            final_str = str(final_val) if not pd.isna(final_val) else 'NULL'
            sqlite_str = str(sqlite_val) if not pd.isna(sqlite_val) else 'NULL'

            if final_str != sqlite_str:
                # Calculate numeric difference if both are numbers
                numeric_diff = None
                pct_change = None
                try:
                    f_num = float(final_val)
                    s_num = float(sqlite_val)
                    numeric_diff = f_num - s_num
                    if s_num != 0:
                        pct_change = round((numeric_diff / s_num) * 100, 2)
                except (ValueError, TypeError):
                    pass  # Not numeric — that's fine, we just won't show a diff

                differences.append({
                    'Table': table_name,
                    'UNITID': unitid,
                    'Institution': inst_names.get(unitid, f"Unknown ({unitid})"),
                    'Variable': col,
                    'Provisional Value': sqlite_str,
                    'Final Value': final_str,
                    'Numeric Difference': numeric_diff,
                    'Percent Change': pct_change,
                    'Change Type': 'Value changed'
                })

    return differences


# ============================================================================
# REPORT GENERATION
# ============================================================================

def save_verification_report(all_differences, year, output_path):
    """
    Save the verification results to an Excel file.

    Creates two sheets:
      - Summary: one row per table showing how many values changed
      - All Changes: every individual difference found

    Args:
        all_differences (list): All difference records from compare_table()
        year (int): Survey year being verified
        output_path (str): Where to save the Excel file
    """
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:

        # ── Sheet 1: Summary ─────────────────────────────────────────────────
        if all_differences:
            diff_df = pd.DataFrame(all_differences)

            # Count changes per table
            summary_data = []
            for table in diff_df['Table'].unique():
                table_diffs = diff_df[diff_df['Table'] == table]
                institutions_affected = table_diffs['UNITID'].nunique()
                summary_data.append({
                    'Table': table,
                    'Total Changes': len(table_diffs),
                    'Institutions Affected': institutions_affected,
                    'Variables Changed': table_diffs['Variable'].nunique()
                        if '— ALL —' not in table_diffs['Variable'].values else 'See detail'
                })

            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)

            # ── Sheet 2: All Changes ──────────────────────────────────────────
            # Reorder columns for readability
            col_order = [
                'Table', 'Institution', 'UNITID', 'Variable',
                'Provisional Value', 'Final Value',
                'Numeric Difference', 'Percent Change', 'Change Type'
            ]
            # Only include columns that exist
            col_order = [c for c in col_order if c in diff_df.columns]
            diff_df[col_order].to_excel(writer, sheet_name='All Changes', index=False)

        else:
            # No differences found — write a confirmation sheet
            confirm_df = pd.DataFrame([{
                'Result': 'NO DIFFERENCES FOUND',
                'Year Verified': year,
                'Date Checked': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'Final File': FINAL_ACCDB_PATH,
                'SQLite Database': DB_PATH,
                'Institutions Checked': len(BCLA_UNITIDS),
            }])
            confirm_df.to_excel(writer, sheet_name='Summary', index=False)

    print(f"\n  ✓ Report saved: {output_path}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print(f"BCLA Data Verification — Survey Year {SURVEY_YEAR}")
    print(f"Comparing provisional SQLite data against final .accdb")
    print("=" * 70)

    # ── Pre-flight checks ────────────────────────────────────────────────────
    errors = []
    if not os.path.exists(FINAL_ACCDB_PATH):
        errors.append(f"Final .accdb not found: {FINAL_ACCDB_PATH}")
    if not os.path.exists(DB_PATH):
        errors.append(f"SQLite database not found: {DB_PATH}")

    if errors:
        print("\n✗ Cannot run — please fix these issues first:")
        for e in errors:
            print(f"  • {e}")
        return

    # ── Connect to both data sources ─────────────────────────────────────────
    print(f"\nConnecting to data sources...")
    accdb_conn = connect_to_accdb(FINAL_ACCDB_PATH)
    sqlite_conn = sqlite3.connect(DB_PATH)

    if accdb_conn is None:
        print("✗ Could not connect to final .accdb. Exiting.")
        sqlite_conn.close()
        return

    # Load institution names for readable output
    inst_names = get_institution_names(sqlite_conn)
    print(f"  ✓ Loaded {len(inst_names)} institution names from SQLite")

    # ── Build table names for this year ──────────────────────────────────────
    table_names = build_table_names(SURVEY_YEAR)
    print(f"\nTables to verify:")
    for ttype, tname in table_names.items():
        print(f"  {ttype.upper():6} → {tname}")

    # ── Compare each table ───────────────────────────────────────────────────
    all_differences = []

    for table_type, table_name in table_names.items():
        print(f"\n{'─'*60}")
        print(f"Comparing: {table_name}")

        # Read from final .accdb
        print(f"  Reading from final .accdb...")
        final_df = read_from_accdb(accdb_conn, table_name, BCLA_UNITIDS)

        if final_df is not None:
            print(f"  ✓ Final: {len(final_df)} BCLA rows, {len(final_df.columns)} columns")
        else:
            print(f"  Skipping {table_name} — not available in final .accdb")
            continue

        # Read from SQLite (provisional data)
        print(f"  Reading from SQLite...")
        sqlite_df = read_from_sqlite(sqlite_conn, table_name)

        if sqlite_df is not None:
            print(f"  ✓ SQLite: {len(sqlite_df)} BCLA rows, {len(sqlite_df.columns)} columns")
        else:
            print(f"  Skipping {table_name} — not in SQLite database")
            continue

        # Run the comparison
        table_diffs = compare_table(table_name, final_df, sqlite_df, inst_names)
        all_differences.extend(table_diffs)

        if table_diffs:
            print(f"  ⚠  {len(table_diffs)} difference(s) found")
        else:
            print(f"  ✓ No differences found")

    # ── Close connections ────────────────────────────────────────────────────
    accdb_conn.close()
    sqlite_conn.close()

    # ── Save report ──────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"BCLA_Verification_{SURVEY_YEAR}_{timestamp}.xlsx"

    if all_differences:
        print(f"⚠  DIFFERENCES FOUND: {len(all_differences)} value(s) changed")
        print(f"   Review the report to decide if posted reports need updating.")
    else:
        print(f"✓ ALL VALUES MATCH — no differences found between provisional")
        print(f"  and final data for BCLA institutions.")
        print(f"  Your posted reports do not need to be updated.")

    save_verification_report(all_differences, SURVEY_YEAR, output_path)

    print(f"\nDone! Report saved as: {output_path}")


if __name__ == "__main__":
    main()
