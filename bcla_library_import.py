"""
BCLA Library Data Import Script
This script imports IPEDS Academic Libraries and Fall Enrollment data from .accdb files
for BCLA member institutions (2019-2024).

Required packages: pandas, pyodbc
Install with: pip install pandas pyodbc
"""

import sqlite3
import pandas as pd
import pyodbc
import os
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

# List of BCLA institution Unit IDs (from bcla-institutions.txt)
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

# Years to process (IPEDS survey years)
YEARS = [2019, 2020, 2021, 2022, 2023]

# SQLite database path
DB_PATH = "bcla_library.sqlite"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def connect_to_accdb(accdb_file):
    """
    Connect to an Access database file.
    
    Args:
        accdb_file (str): Path to the .accdb file
        
    Returns:
        pyodbc.Connection: Connection to the database
    """
    # This creates a connection string for Microsoft Access
    # The connection string tells Python how to connect to the Access database
    conn_str = (
        r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
        f'DBQ={accdb_file};'
    )
    
    try:
        conn = pyodbc.connect(conn_str)
        print(f"✓ Connected to {os.path.basename(accdb_file)}")
        return conn
    except Exception as e:
        print(f"✗ Error connecting to {accdb_file}: {e}")
        return None


def get_table_from_accdb(conn, table_name, filter_unitids=True):
    """
    Extract a specific table from the Access database.
    
    Args:
        conn: pyodbc connection to the Access database
        table_name (str): Name of the table to extract
        filter_unitids (bool): Whether to filter by BCLA institution IDs
        
    Returns:
        pandas.DataFrame: The extracted data, or None if table doesn't exist
    """
    try:
        # First check if the table exists
        cursor = conn.cursor()
        tables = [row.table_name for row in cursor.tables(tableType='TABLE')]
        
        if table_name not in tables:
            print(f"  Warning: Table {table_name} not found in database")
            return None
        
        # Read the table into a pandas DataFrame
        query = f"SELECT * FROM [{table_name}]"
        df = pd.read_sql(query, conn)
        
        print(f"  Read {len(df)} rows from {table_name}")
        
        # Filter by BCLA institution IDs if requested
        if filter_unitids and 'UNITID' in df.columns:
            df = df[df['UNITID'].isin(BCLA_UNITIDS)]
            print(f"  Filtered to {len(df)} BCLA institutions")
        
        return df
        
    except Exception as e:
        print(f"  Error reading table {table_name}: {e}")
        return None


def process_year(year, accdb_path):
    """
    Process all tables for a specific year from an accdb file.
    
    Args:
        year (int): The IPEDS survey year
        accdb_path (str): Path to the .accdb file
        
    Returns:
        dict: Dictionary with table names as keys and DataFrames as values
    """
    print(f"\n{'='*70}")
    print(f"Processing Year {year}")
    print(f"{'='*70}")
    
    # Connect to the Access database
    conn = connect_to_accdb(accdb_path)
    if not conn:
        return {}
    
    # Dictionary to store all extracted tables
    tables_data = {}
    
    # Define which tables we need for this year
    # Table numbers are used to match tables across years
    # From project-variables-accdb.csv:
    # - Table 27 = Fall Enrollment (DRVEF)
    # - Table 160 = Academic Libraries (AL)
    # - Table 161 = Derived Academic Library Variables (DRVAL)
    
    tables_to_extract = [
        f'DRVEF{year}',    # Fall Enrollment (FTE)
        f'AL{year}',       # Academic Libraries
        f'DRVAL{year}',    # Derived Academic Library Variables
    ]
    
    # Also get HD (Directory) table for institution names
    tables_to_extract.append(f'HD{year}')
    
    # Extract each table
    for table_name in tables_to_extract:
        print(f"\nExtracting {table_name}...")
        
        # HD table shouldn't be filtered by UNITID in case we need all institutions
        # But we'll filter it when we save to SQLite
        filter_by_unitid = (table_name != f'HD{year}')
        
        df = get_table_from_accdb(conn, table_name, filter_unitids=filter_by_unitid)
        
        if df is not None:
            tables_data[table_name.lower()] = df
    
    # Close the connection
    conn.close()
    print(f"\n✓ Completed processing year {year}")
    
    return tables_data


def save_to_sqlite(tables_dict, db_path):
    """
    Save all extracted tables to a SQLite database.
    
    Args:
        tables_dict (dict): Dictionary with table names and DataFrames
        db_path (str): Path to the SQLite database file
    """
    print(f"\n{'='*70}")
    print(f"Saving to SQLite database: {db_path}")
    print(f"{'='*70}")
    
    # Connect to SQLite database (creates it if it doesn't exist)
    conn = sqlite3.connect(db_path)
    
    # Save each table
    for table_name, df in tables_dict.items():
        # Filter HD table to only BCLA institutions when saving
        if 'hd' in table_name and 'UNITID' in df.columns:
            df = df[df['UNITID'].isin(BCLA_UNITIDS)]
            # Only keep UNITID and INSTNM columns
            if 'INSTNM' in df.columns:
                df = df[['UNITID', 'INSTNM']]
        
        # Write to SQLite
        # if_exists='replace' means if the table already exists, replace it
        # index=False means don't save the pandas row numbers as a column
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"✓ Saved {table_name}: {len(df)} rows")
    
    conn.close()
    print(f"\n✓ All tables saved to {db_path}")


def verify_database(db_path):
    """
    Verify the contents of the SQLite database.
    
    Args:
        db_path (str): Path to the SQLite database file
    """
    print(f"\n{'='*70}")
    print(f"Database Verification")
    print(f"{'='*70}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get list of all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print(f"\nTables in database:")
    for table in tables:
        table_name = table[0]
        
        # Count rows in this table
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        
        # Get column names
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        
        print(f"\n  {table_name}:")
        print(f"    Rows: {count}")
        print(f"    Columns: {len(columns)}")
        print(f"    Column names: {', '.join(columns[:5])}{'...' if len(columns) > 5 else ''}")
    
    conn.close()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main function to run the import process."""
    
    print("="*70)
    print("BCLA Library Data Import")
    print("="*70)
    print(f"Processing {len(YEARS)} years: {YEARS}")
    print(f"Extracting data for {len(BCLA_UNITIDS)} BCLA institutions")
    print(f"Output database: {DB_PATH}")
    
    # Check if database already exists
    if os.path.exists(DB_PATH):
        response = input(f"\n⚠ Database {DB_PATH} already exists. Overwrite? (yes/no): ")
        if response.lower() != 'yes':
            print("Import cancelled.")
            return
        # Remove existing database
        os.remove(DB_PATH)
        print(f"✓ Removed existing database")
    
    # Dictionary to store all tables from all years
    all_tables = {}
    
    # Process each year
    for year in YEARS:
        # Construct the expected filename for the accdb file
        # IPEDS uses format like "IPEDS201920.accdb" for 2019-20 academic year
        # So year 2019 corresponds to "IPEDS201920.accdb"
        accdb_filename = f"IPEDS{year}{str(year+1)[-2:]}.accdb"
        
        # Check if file exists in current directory
        if not os.path.exists(accdb_filename):
            print(f"\n⚠ Warning: {accdb_filename} not found")
            print(f"  Please ensure the file is in the current directory")
            continue
        
        # Convert to absolute path (required by Access driver)
        accdb_path = os.path.abspath(accdb_filename)
                
        # Process this year
        year_tables = process_year(year, accdb_path)
        
        # Add to our collection
        all_tables.update(year_tables)
    
    # Save everything to SQLite
    if all_tables:
        save_to_sqlite(all_tables, DB_PATH)
        verify_database(DB_PATH)
        
        print(f"\n{'='*70}")
        print("Import Complete!")
        print(f"{'='*70}")
        print(f"\nNext steps:")
        print(f"1. Run the variable titles import script")
        print(f"2. Run the report generator")
    else:
        print("\n⚠ No data was imported. Please check that .accdb files exist.")


if __name__ == "__main__":
    main()
