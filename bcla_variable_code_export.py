"""
BCLA Variable Code Export for Airtable
=======================================
This script reads the variable_titles table from bcla_library.sqlite
and outputs a CSV file ready to load into the Variable_Code table
in the BCLA Academic Libraries Survey Airtable base.

The output CSV has one row per measurement variable in Historical_IPEDS_Data,
with fields matching the Variable_Code table structure:
  - Variable_Code        : Your Airtable field name (e.g., AL_Total_Expenditures)
  - Friendly_Label       : Human-readable label
  - Description          : What the variable measures
  - Unit                 : Dollars / Count / FTE / Percent / Ratio
  - IPEDS_Variable_Code  : Original IPEDS column name (e.g., LEXPTOT)
  - IPEDS_Table_Source   : Which IPEDS table it comes from (AL, DRVAL, DRVEF, F)
  - IPEDS_Variable_Title : Official title from IPEDS documentation
  - In_Historical_Data   : Yes/No — is this in Historical_IPEDS_Data?
  - In_Survey_Responses  : Yes/No — is this in Survey_Responses?
  - Survey_Question_Text : (left blank for you to fill in)
  - Available_Since      : First year this variable appears in your database
  - Discontinued         : Yes/No — did IPEDS retire this variable?
  - Notes                : Caveats, calculation notes, known gaps

How to run:
  py bcla_variable_code_export.py

Output:
  variable_code_export_YYYYMMDD_HHMMSS.csv  (in the same folder as the script)

Required packages: pandas, sqlite3 (sqlite3 is built into Python)
Install if needed: pip install pandas --break-system-packages
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

# Path to your SQLite database (same folder as this script)
DB_PATH = "bcla_library.sqlite"

# ============================================================================
# REFERENCE DICTIONARY
# ============================================================================
#
# This dictionary is the bridge between your Airtable field names and the
# original IPEDS variable codes stored in bcla_library.sqlite.
#
# Structure of each entry:
#   "Airtable_Field_Name": {
#       "ipeds_code"   : the column name in the .accdb file (None if calculated)
#       "ipeds_title"  : official IPEDS variable title (hardcoded here as the primary source)
#       "source_table" : which IPEDS table it comes from
#       "unit"         : what kind of number it is
#       "friendly"     : a short human-readable label
#       "description"  : what it measures
#       "since"        : first year this variable is available in the pipeline
#       "discontinued" : whether IPEDS has retired this variable
#       "notes"        : any caveats worth documenting
#   }
#
# Why ipeds_title is hardcoded: The variable_titles table in bcla_library.sqlite
# is built from IPEDS tablesDoc Excel files, which contain titles for common
# survey variables but are missing many AL-specific sub-variables. Hardcoding
# the titles here makes the script self-contained and accurate regardless of
# what is or isn't in the database.
#
# Fields marked ipeds_code=None are calculated values (sums) that don't have
# a direct IPEDS code — they were computed in bcla_airtable_export.py.

VARIABLE_REFERENCE = {

    # ---- FINANCE (from F_F2 tables) ----------------------------------------
    "Total_Expenses": {
        "ipeds_code":   "F2E131",
        "ipeds_title":  "Total expenses-Total amount",
        "source_table": "F",
        "unit":         "Dollars",
        "friendly":     "Total Institutional Expenses",
        "description":  "Total expenses for the institution from IPEDS Finance survey (FASB/GASB Form 2, line 31). Used as the denominator for library spending comparisons.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "Institutional total, not library-specific. Pulled from F{yy}{yy}_F2 table.",
    },

    # ---- FALL ENROLLMENT (from DRVEF tables) --------------------------------
    "DRVEF_FTE": {
        "ipeds_code":   "FTE",
        "ipeds_title":  "Full-time equivalent fall enrollment",
        "source_table": "DRVEF",
        "unit":         "FTE",
        "friendly":     "Full-Time Equivalent Fall Enrollment",
        "description":  "Derived full-time equivalent fall enrollment. Calculated by IPEDS: full-time students + (1/3 × part-time students). Used for per-student benchmarking.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "Preferred over raw headcount for cross-institution comparisons. IPEDS-derived variable.",
    },

    # ---- ACADEMIC LIBRARIES — EXPENDITURES (from AL tables) ----------------
    "AL_Total_Expenditures": {
        "ipeds_code":   "LEXPTOT",
        "ipeds_title":  "Total expenditures (salaries/wages, benefits, materials/services, and operations/maintenance)",
        "source_table": "AL",
        "unit":         "Dollars",
        "friendly":     "Total Library Expenditures",
        "description":  "Total library expenditures including salaries, benefits, materials, and operations.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "",
    },
    "AL_Salaries_Wages": {
        "ipeds_code":   "LEXPSAL",
        "ipeds_title":  "Salaries and wages",
        "source_table": "AL",
        "unit":         "Dollars",
        "friendly":     "Library Salaries and Wages",
        "description":  "Total salaries and wages paid to library staff.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "",
    },
    "AL_Fringe_Benefits": {
        "ipeds_code":   "LEXPBEN",
        "ipeds_title":  "Fringe benefits",
        "source_table": "AL",
        "unit":         "Dollars",
        "friendly":     "Library Fringe Benefits",
        "description":  "Fringe benefits paid for library staff.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "",
    },
    "AL_Onetime_Purchases": {
        "ipeds_code":   "LEXPODDI",
        "ipeds_title":  "One-time purchases",
        "source_table": "AL",
        "unit":         "Dollars",
        "friendly":     "One-Time Materials Purchases",
        "description":  "One-time purchases of library materials (e.g., monograph purchases, non-recurring digital purchases).",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "",
    },
    "AL_Ongoing_Subscriptions": {
        "ipeds_code":   "LEXPODDO",
        "ipeds_title":  "Ongoing commitments/subscriptions",
        "source_table": "AL",
        "unit":         "Dollars",
        "friendly":     "Ongoing Materials Subscriptions",
        "description":  "Ongoing subscription costs for library materials (e.g., periodicals, database subscriptions).",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "",
    },
    "AL_Total_Materials": {
        "ipeds_code":   "LEXPMATP",
        "ipeds_title":  "Total materials/services expenditures",
        "source_table": "AL",
        "unit":         "Dollars",
        "friendly":     "Total Materials Expenditures",
        "description":  "Total expenditures on library materials. Sum of one-time purchases and ongoing subscriptions.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "",
    },
    "AL_Operations": {
        "ipeds_code":   "LEXPOPER",
        "ipeds_title":  "Operations and maintenance expenditures",
        "source_table": "AL",
        "unit":         "Dollars",
        "friendly":     "Library Operations Expenditures",
        "description":  "Total operations and maintenance expenditures for the library.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "",
    },
    "AL_Other_Materials": {
        "ipeds_code":   "LEXPMATO",
        "ipeds_title":  "Other materials/services expenditures",
        "source_table": "AL",
        "unit":         "Dollars",
        "friendly":     "Other Materials Expenditures",
        "description":  "Expenditures on materials not captured in one-time or ongoing categories.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "Added to pipeline in 2025. Check availability for earlier years.",
    },
    "AL_Preservation": {
        "ipeds_code":   "LEXPMAPR",
        "ipeds_title":  "Preservation expenditures",
        "source_table": "AL",
        "unit":         "Dollars",
        "friendly":     "Preservation Expenditures",
        "description":  "Expenditures on preservation and conservation of library materials.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "Added to pipeline in 2025. Check availability for earlier years.",
    },
    "AL_Other_Operations": {
        "ipeds_code":   "LEXPOPEO",
        "ipeds_title":  "Other operations and maintenance expenditures",
        "source_table": "AL",
        "unit":         "Dollars",
        "friendly":     "Other Operations Expenditures",
        "description":  "Other operations expenditures not captured in the main operations category.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "Added to pipeline in 2025. Check availability for earlier years.",
    },

    # ---- ACADEMIC LIBRARIES — COLLECTIONS (from AL tables) -----------------
    "AL_Physical_Books": {
        "ipeds_code":   "LBKVOL",
        "ipeds_title":  "Books - physical",
        "source_table": "AL",
        "unit":         "Count",
        "friendly":     "Physical Books (Volumes)",
        "description":  "Number of physical book volumes held by the library.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "",
    },
    "AL_Electronic_Books": {
        "ipeds_code":   "LBKENE",
        "ipeds_title":  "Books - digital/electronic",
        "source_table": "AL",
        "unit":         "Count",
        "friendly":     "Electronic Books",
        "description":  "Number of electronic book titles accessible to users.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "",
    },
    "AL_Electronic_Databases": {
        "ipeds_code":   "LDBASE",
        "ipeds_title":  "Databases",
        "source_table": "AL",
        "unit":         "Count",
        "friendly":     "Electronic Databases",
        "description":  "Number of electronic database subscriptions or licenses held.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "",
    },
    "AL_Physical_Media": {
        "ipeds_code":   "LAVVOL",
        "ipeds_title":  "Media - physical",
        "source_table": "AL",
        "unit":         "Count",
        "friendly":     "Physical Media (Audiovisual)",
        "description":  "Number of physical audiovisual units held (DVDs, CDs, etc.).",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "",
    },
    "AL_Electronic_Media": {
        "ipeds_code":   "LAVENE",
        "ipeds_title":  "Media - digital/electronic",
        "source_table": "AL",
        "unit":         "Count",
        "friendly":     "Electronic Media (Audiovisual)",
        "description":  "Number of electronic audiovisual units accessible to users.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "Added to pipeline in 2025. Check availability for earlier years.",
    },
    "AL_Physical_Serials": {
        "ipeds_code":   "LSERVOL",
        "ipeds_title":  "Serials - physical",
        "source_table": "AL",
        "unit":         "Count",
        "friendly":     "Physical Serials",
        "description":  "Number of physical serial subscriptions held (print journals, newspapers).",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "",
    },
    "AL_Electronic_Serials": {
        "ipeds_code":   "LSERENE",
        "ipeds_title":  "Serials - digital/electronic",
        "source_table": "AL",
        "unit":         "Count",
        "friendly":     "Electronic Serials",
        "description":  "Number of electronic serial titles accessible to users.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "Added to pipeline in 2025. Check availability for earlier years.",
    },
    "AL_Total_Physical_Collections": {
        "ipeds_code":   None,
        "ipeds_title":  "",
        "source_table": "AL",
        "unit":         "Count",
        "friendly":     "Total Physical Collections",
        "description":  "Sum of all physical collection items: physical books + physical media + physical serials.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "Calculated field (not a direct IPEDS variable). Formula: LBKVOL + LAVVOL + LSERVOL.",
    },
    "AL_Total_Electronic_Collections": {
        "ipeds_code":   None,
        "ipeds_title":  "",
        "source_table": "AL",
        "unit":         "Count",
        "friendly":     "Total Electronic Collections",
        "description":  "Sum of all electronic collection items: electronic books + electronic databases + electronic media + electronic serials.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "Calculated field (not a direct IPEDS variable). Formula: LBKENE + LDBASE + LAVENE + LSERENE.",
    },
    "AL_Total_Collections": {
        "ipeds_code":   None,
        "ipeds_title":  "",
        "source_table": "AL",
        "unit":         "Count",
        "friendly":     "Total Collections",
        "description":  "Sum of all physical and electronic collection items.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "Calculated field (not a direct IPEDS variable). Formula: Total Physical + Total Electronic.",
    },

    # ---- ACADEMIC LIBRARIES — CIRCULATION (from AL tables) -----------------
    "AL_Total_Circulations": {
        "ipeds_code":   "LCIRCTP",
        "ipeds_title":  "Physical and electronic circulations/transactions - total",
        "source_table": "AL",
        "unit":         "Count",
        "friendly":     "Total Circulations",
        "description":  "Total number of items circulated (checked out) during the year.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "",
    },
    "AL_Physical_Circulations": {
        "ipeds_code":   "LCIRCVOL",
        "ipeds_title":  "Physical circulations",
        "source_table": "AL",
        "unit":         "Count",
        "friendly":     "Physical Circulations",
        "description":  "Number of physical items circulated (checked out) during the year.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "Added to pipeline in 2025. Check availability for earlier years.",
    },
    "AL_Digital_Circulations": {
        "ipeds_code":   "LCIRCELE",
        "ipeds_title":  "Electronic circulations/transactions",
        "source_table": "AL",
        "unit":         "Count",
        "friendly":     "Digital Circulations",
        "description":  "Number of electronic/digital items circulated during the year.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "Added to pipeline in 2025. Check availability for earlier years.",
    },
    "AL_ILL_Received": {
        "ipeds_code":   "LILLREC",
        "ipeds_title":  "Interlibrary loans received",
        "source_table": "AL",
        "unit":         "Count",
        "friendly":     "Interlibrary Loans Received",
        "description":  "Number of interlibrary loan items borrowed from other libraries.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "",
    },
    "AL_ILL_Provided": {
        "ipeds_code":   "LILLPRO",
        "ipeds_title":  "Interlibrary loans provided",
        "source_table": "AL",
        "unit":         "Count",
        "friendly":     "Interlibrary Loans Provided",
        "description":  "Number of interlibrary loan items lent to other libraries.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "",
    },

    # ---- ACADEMIC LIBRARIES — STAFFING (from AL tables) --------------------
    "AL_Total_Staff_FTE": {
        "ipeds_code":   "LTOTSTF",
        "ipeds_title":  "Total FTE staff",
        "source_table": "AL",
        "unit":         "FTE",
        "friendly":     "Total Library Staff FTE",
        "description":  "Total full-time equivalent library staff, including all categories.",
        "since":        "2020",
        "discontinued": "No",
        "notes":        "",
    },
    "AL_Librarians_FTE": {
        "ipeds_code":   "LFTLBR",
        "ipeds_title":  "Librarians - FTE",
        "source_table": "AL",
        "unit":         "FTE",
        "friendly":     "Librarians FTE",
        "description":  "Full-time equivalent count of professional librarians (MLS/MLIS required).",
        "since":        "2020",
        "discontinued": "No",
        "notes":        "",
    },
    "AL_Other_Professional_FTE": {
        "ipeds_code":   "LFTOTHR",
        "ipeds_title":  "Other professional staff - FTE",
        "source_table": "AL",
        "unit":         "FTE",
        "friendly":     "Other Professional Staff FTE",
        "description":  "Full-time equivalent count of other professional staff (non-librarian professionals).",
        "since":        "2020",
        "discontinued": "No",
        "notes":        "",
    },
    "AL_Other_Paid_Staff_FTE": {
        "ipeds_code":   "LFTSUP",
        "ipeds_title":  "All other paid staff - FTE",
        "source_table": "AL",
        "unit":         "FTE",
        "friendly":     "Other Paid Staff FTE",
        "description":  "Full-time equivalent count of support/paraprofessional staff.",
        "since":        "2020",
        "discontinued": "No",
        "notes":        "",
    },
    "AL_Student_Assistants_FTE": {
        "ipeds_code":   "LFTSTU",
        "ipeds_title":  "Student assistants - FTE",
        "source_table": "AL",
        "unit":         "FTE",
        "friendly":     "Student Assistants FTE",
        "description":  "Full-time equivalent count of student assistant workers.",
        "since":        "2020",
        "discontinued": "No",
        "notes":        "",
    },

    # ---- DERIVED ACADEMIC LIBRARY VARIABLES (from DRVAL tables) ------------
    "DRVAL_Expenditures_Per_FTE": {
        "ipeds_code":   "LEXPFTE",
        "ipeds_title":  "Total library expenditures per FTE enrollment",
        "source_table": "DRVAL",
        "unit":         "Dollars",
        "friendly":     "Library Expenditures per FTE Student",
        "description":  "Total library expenditures divided by full-time equivalent enrollment. An IPEDS-calculated benchmarking metric.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "IPEDS-derived variable. Calculated by NCES, not computed in this pipeline.",
    },
    "DRVAL_Pct_Salaries": {
        "ipeds_code":   "LSALPCT",
        "ipeds_title":  "Salaries and wages as a percent of total library expenditures",
        "source_table": "DRVAL",
        "unit":         "Percent",
        "friendly":     "Salaries as % of Library Expenditures",
        "description":  "Salaries and wages as a percentage of total library expenditures.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "IPEDS-derived variable. Calculated by NCES, not computed in this pipeline.",
    },
    "DRVAL_Pct_Subscriptions": {
        "ipeds_code":   "LSUBPCT",
        "ipeds_title":  "Ongoing commitments/subscriptions as a percent of total materials expenditures",
        "source_table": "DRVAL",
        "unit":         "Percent",
        "friendly":     "Subscriptions as % of Materials Expenditures",
        "description":  "Ongoing subscriptions as a percentage of total materials expenditures.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "IPEDS-derived variable. Calculated by NCES, not computed in this pipeline.",
    },
    "DRVAL_Pct_Physical_Books": {
        "ipeds_code":   "LBKPCT",
        "ipeds_title":  "Books - physical as a percent of total collections",
        "source_table": "DRVAL",
        "unit":         "Percent",
        "friendly":     "Physical Books as % of Total Collections",
        "description":  "Physical book volumes as a percentage of total collection items.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "IPEDS-derived variable. Calculated by NCES, not computed in this pipeline.",
    },
    "DRVAL_Pct_Electronic_Books": {
        "ipeds_code":   "LEBKPCT",
        "ipeds_title":  "Books - digital/electronic as a percent of total collections",
        "source_table": "DRVAL",
        "unit":         "Percent",
        "friendly":     "Electronic Books as % of Total Collections",
        "description":  "Electronic book titles as a percentage of total collection items.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "IPEDS-derived variable. Calculated by NCES, not computed in this pipeline.",
    },
    "DRVAL_Pct_Electronic_Media": {
        "ipeds_code":   "LAVEPCT",
        "ipeds_title":  "Media - digital/electronic as a percent of total collections",
        "source_table": "DRVAL",
        "unit":         "Percent",
        "friendly":     "Electronic Media as % of Total Collections",
        "description":  "Electronic audiovisual items as a percentage of total collection items.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "IPEDS-derived variable. Added to pipeline in 2025. Check availability for earlier years.",
    },
    "DRVAL_Pct_Electronic_Serials": {
        "ipeds_code":   "LSERPCT",
        "ipeds_title":  "Serials - digital/electronic as a percent of total collections",
        "source_table": "DRVAL",
        "unit":         "Percent",
        "friendly":     "Electronic Serials as % of Total Collections",
        "description":  "Electronic serial titles as a percentage of total collection items.",
        "since":        "2019",
        "discontinued": "No",
        "notes":        "IPEDS-derived variable. Added to pipeline in 2025. Check availability for earlier years.",
    },
}

# ============================================================================
# FUNCTIONS
# ============================================================================

def connect_to_database(db_path):
    """
    Connect to the SQLite database and verify it exists.

    What this does: Opens a connection to your bcla_library.sqlite file
    so we can run queries against it.

    Args:
        db_path (str): File path to the SQLite database

    Returns:
        sqlite3.Connection: A database connection object, or None if not found
    """
    if not os.path.exists(db_path):
        print(f"✗ Error: Database not found at '{db_path}'")
        print("  Please make sure bcla_library.sqlite is in the same folder as this script.")
        return None

    conn = sqlite3.connect(db_path)
    print(f"✓ Connected to {db_path}")
    return conn


def load_variable_titles(conn):
    """
    Load the variable_titles table from SQLite into a DataFrame.

    What this does: Reads the lookup table that maps IPEDS variable codes
    (like LEXPTOT) to their official titles (like 'Total library expenditures').
    This table was created by bcla_variable_titles.py.

    Args:
        conn: SQLite database connection

    Returns:
        pandas.DataFrame: The variable_titles table, or None if not found
    """
    cursor = conn.cursor()

    # Check if the variable_titles table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='variable_titles'")
    if not cursor.fetchone():
        print("✗ Error: 'variable_titles' table not found in database.")
        print("  Please run bcla_variable_titles.py first to create this table.")
        return None

    # Load the full table
    df = pd.read_sql_query("SELECT * FROM variable_titles", conn)
    print(f"✓ Loaded variable_titles table: {len(df)} variable records")

    return df


def get_ipeds_title(var_titles_df, ipeds_code):
    """
    Look up the official IPEDS variable title for a given variable code.

    What this does: Searches the variable_titles DataFrame for a specific
    IPEDS code and returns its official title. For example, passing 'LEXPTOT'
    returns 'Total library expenditures'.

    Args:
        var_titles_df: The variable_titles DataFrame from load_variable_titles()
        ipeds_code (str): The IPEDS variable code (e.g., 'LEXPTOT')

    Returns:
        str: The official IPEDS title, or an empty string if not found
    """
    if ipeds_code is None or var_titles_df is None:
        return ""

    # Look for the code in the varName column (case-sensitive)
    match = var_titles_df[var_titles_df['varName'] == ipeds_code]

    if len(match) > 0:
        return match.iloc[0]['current_varTitle']
    else:
        # Try case-insensitive match as a fallback
        match = var_titles_df[var_titles_df['varName'].str.upper() == ipeds_code.upper()]
        if len(match) > 0:
            return match.iloc[0]['current_varTitle']
        return ""


def check_title_has_variations(var_titles_df, ipeds_code):
    """
    Check whether an IPEDS variable's title changed across survey years.

    What this does: The IPEDS vartable documentation sometimes updates
    variable titles slightly from year to year. This function returns
    True if that happened for a given variable — useful information for
    the Notes field.

    Args:
        var_titles_df: The variable_titles DataFrame
        ipeds_code (str): The IPEDS variable code

    Returns:
        bool: True if the title changed across years, False otherwise
    """
    if ipeds_code is None or var_titles_df is None:
        return False

    match = var_titles_df[var_titles_df['varName'] == ipeds_code]
    if len(match) > 0:
        return bool(match.iloc[0]['has_variations'])

    return False


def build_output_rows(var_titles_df):
    """
    Build the list of rows for the output CSV.

    What this does: This is the main assembly function. It loops through
    every entry in VARIABLE_REFERENCE, looks up the official IPEDS title
    from the database, and assembles the full row for the Variable_Code table.

    Args:
        var_titles_df: The variable_titles DataFrame (may be None if db is missing
                       the table — the script will still run with blank IPEDS titles)

    Returns:
        list: A list of dictionaries, one per variable
    """
    rows = []

    for airtable_field, ref in VARIABLE_REFERENCE.items():

        ipeds_code  = ref["ipeds_code"]
        source      = ref["source_table"]

        # Use the hardcoded IPEDS title first (primary source).
        # Fall back to the database lookup only if no hardcoded title is set.
        # This is necessary because the variable_titles table in bcla_library.sqlite
        # is missing many AL-specific variable titles.
        ipeds_title = ref.get("ipeds_title", "")
        if not ipeds_title:
            ipeds_title = get_ipeds_title(var_titles_df, ipeds_code)

        # Check if the title changed across years (and append a note if so)
        notes = ref["notes"]
        if ipeds_code and check_title_has_variations(var_titles_df, ipeds_code):
            variation_note = f"Note: IPEDS variable title changed across survey years."
            notes = f"{notes} {variation_note}".strip() if notes else variation_note

        row = {
            "Variable_Code":        airtable_field,
            "Friendly_Label":       ref["friendly"],
            "Description":          ref["description"],
            "Unit":                 ref["unit"],
            "IPEDS_Variable_Code":  ipeds_code if ipeds_code else "",
            "IPEDS_Table_Source":   source,
            "IPEDS_Variable_Title": ipeds_title,
            "In_Historical_Data":   "Yes",    # You can update this manually in Airtable
            "In_Survey_Responses":  "Yes",    # You can update this manually in Airtable
            "Survey_Question_Text": "",       # Fill in manually for any future survey fields
            "Available_Since":      ref["since"],
            "Discontinued":         ref["discontinued"],
            "Notes":                notes,
        }

        rows.append(row)

    return rows


def save_to_csv(rows, output_path):
    """
    Write the assembled rows to a CSV file.

    What this does: Takes the list of row dictionaries and writes them
    to a CSV file that Airtable can import directly.

    Args:
        rows (list): List of row dictionaries from build_output_rows()
        output_path (str): Path and filename for the output CSV

    Returns:
        bool: True if saved successfully
    """
    df = pd.DataFrame(rows)

    # Column order — matches the Variable_Code table structure we designed
    column_order = [
        "Variable_Code",
        "Friendly_Label",
        "Description",
        "Unit",
        "IPEDS_Variable_Code",
        "IPEDS_Table_Source",
        "IPEDS_Variable_Title",
        "In_Historical_Data",
        "In_Survey_Responses",
        "Survey_Question_Text",
        "Available_Since",
        "Discontinued",
        "Notes",
    ]

    df = df[column_order]
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    # utf-8-sig adds a BOM (byte order mark) that helps Excel and Airtable
    # read special characters correctly

    print(f"✓ Saved {len(df)} rows to: {output_path}")
    return True


def print_summary(rows):
    """
    Print a brief summary of the output before saving.

    Args:
        rows (list): The assembled rows
    """
    print(f"\n{'='*60}")
    print("Output Summary")
    print(f"{'='*60}")
    print(f"Total variables: {len(rows)}")

    # Count by source table
    from collections import Counter
    source_counts = Counter(r["IPEDS_Table_Source"] for r in rows)
    print("\nVariables by IPEDS source table:")
    for source, count in sorted(source_counts.items()):
        print(f"  {source:8}: {count}")

    # Count calculated fields (no IPEDS code)
    calc_count = sum(1 for r in rows if not r["IPEDS_Variable_Code"])
    print(f"\nCalculated fields (no direct IPEDS code): {calc_count}")

    # Count how many have IPEDS titles (hardcoded or from database)
    titled_count = sum(1 for r in rows if r["IPEDS_Variable_Title"])
    missing_count = len(rows) - titled_count
    print(f"Variables with IPEDS titles populated: {titled_count}")
    if missing_count > 0:
        print(f"Variables without titles (calculated fields): {missing_count}")

    print(f"\nNote: 'In_Survey_Responses' is set to 'Yes' for all rows.")
    print("Update this manually in Airtable if Survey_Responses fields are adjusted.")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main function — connects to the database and generates the CSV."""

    print("="*60)
    print("BCLA Variable Code Export for Airtable")
    print("="*60)

    # Step 1: Connect to the database
    conn = connect_to_database(DB_PATH)

    # Step 2: Load variable titles from the database
    # (The script will still work if this fails — IPEDS titles will just be blank)
    var_titles_df = None
    if conn:
        var_titles_df = load_variable_titles(conn)
        if var_titles_df is None:
            print("  Continuing without IPEDS titles from database.")
            print("  The IPEDS_Variable_Title column will be blank.")
    else:
        print("  Continuing without database. IPEDS_Variable_Title will be blank.")

    # Step 3: Build the output rows
    print(f"\nBuilding Variable_Code records...")
    rows = build_output_rows(var_titles_df)
    print(f"✓ Built {len(rows)} records")

    # Step 4: Print a summary
    print_summary(rows)

    # Step 5: Save to CSV with a timestamp in the filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"variable_code_export_{timestamp}.csv"

    print(f"\n{'='*60}")
    print("Saving CSV")
    print(f"{'='*60}")
    save_to_csv(rows, output_filename)

    print(f"\n{'='*60}")
    print("Done!")
    print(f"{'='*60}")
    print(f"\nNext steps:")
    print(f"  1. Open {output_filename} and review the contents")
    print(f"  2. In Airtable, go to the Variable_Code table")
    print(f"  3. Use Add records > Import CSV to load the file")
    print(f"  4. After import, update 'In_Survey_Responses' for any fields")
    print(f"     that will also appear in your Survey_Responses table")

    # Close the database connection
    if conn:
        conn.close()


if __name__ == "__main__":
    main()
