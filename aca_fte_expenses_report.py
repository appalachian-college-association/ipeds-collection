"""
ACA Library FTE and Expenses Report Generator
This script generates simplified Excel reports with just FTE enrollment and Total Expenses.

Data Sources:
- Historical years (2019-2023): SQLite database (bcla_library.sqlite)
- Most recent year: CSV export from IPEDS Data Center (aca-ipeds-fte-f2e131-{year}.csv)

Required packages: pandas, openpyxl
Install with: pip install pandas openpyxl --break-system-packages
"""

import sqlite3
import pandas as pd
import os
from datetime import datetime
import glob

# ============================================================================
# CONFIGURATION
# ============================================================================

# SQLite database path
DB_PATH = "bcla_library.sqlite"

# CSV file pattern for IPEDS Data Center exports
# Example: aca-ipeds-fte-f2e131-2024.csv
CSV_PATTERN = "aca-ipeds-fte-f2e131-*.csv"

# ============================================================================
# FUNCTIONS
# ============================================================================

def get_database_connection():
    """
    Connect to the SQLite database.
    
    Returns:
        sqlite3.Connection: Database connection, or None if database doesn't exist
    """
    if not os.path.exists(DB_PATH):
        print(f"⚠ Warning: Database {DB_PATH} not found")
        print("Historical data will not be available")
        return None
    
    return sqlite3.connect(DB_PATH)


def get_available_years_from_db(conn):
    """
    Get a list of years available in the SQLite database.
    
    Args:
        conn: SQLite database connection
        
    Returns:
        list: Sorted list of years (as strings)
    """
    if conn is None:
        return []
    
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    years = set()
    
    # Look for DRVEF and F tables to extract years
    for table in tables:
        # DRVEF tables (e.g., drvef2019, drvef2020)
        if table.lower().startswith('drvef'):
            year = ''.join(filter(str.isdigit, table))
            if year and len(year) == 4:
                years.add(year)
        
        # Finance tables (e.g., f2223_f2 for 2023)
        elif table.lower().startswith('f') and '_f2' in table.lower():
            year_part = ''.join(filter(str.isdigit, table))[:4]
            # Convert YYyy to 20yy (e.g., '2223' -> '2023')
            if len(year_part) == 4:
                year = '20' + year_part[2:4]
                years.add(year)
    
    return sorted(years)


def find_csv_files():
    """
    Find all CSV files matching the pattern in the current directory.
    
    Returns:
        dict: Dictionary mapping year to filename
    """
    csv_files = {}
    
    # Find all matching CSV files
    for filepath in glob.glob(CSV_PATTERN):
        filename = os.path.basename(filepath)
        
        # Extract year from filename
        # Pattern: aca-ipeds-fte-f2e131-2024.csv
        parts = filename.split('-')
        if len(parts) >= 4:
            year_str = parts[-1].replace('.csv', '')
            if year_str.isdigit() and len(year_str) == 4:
                csv_files[year_str] = filepath
    
    return csv_files


def get_data_from_db(conn, year):
    """
    Extract FTE and Total Expenses data for a specific year from the database.
    
    Args:
        conn: SQLite database connection
        year (str): Year to extract (e.g., '2019', '2020')
        
    Returns:
        pandas.DataFrame: DataFrame with UNITID, Institution Name, Total Expenses, and FTE
    """
    cursor = conn.cursor()
    
    # Get table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    # Find the HD table for institution names
    hd_tables = [t for t in tables if t.lower().startswith('hd')]
    
    # Use the most recent HD table
    hd_table = sorted(hd_tables)[-1] if hd_tables else None
    
    # Build the data dictionary
    data = {}
    
    # Start with institution IDs and names
    if hd_table:
        query = f"SELECT UNITID, INSTNM FROM {hd_table}"
        institutions_df = pd.read_sql_query(query, conn)
        
        for _, row in institutions_df.iterrows():
            unitid = row['UNITID']
            data[unitid] = {
                'UNITID': unitid,
                'Institution Name': row['INSTNM']
            }
    
    # Get FTE from DRVEF table
    drvef_table = f"drvef{year}"
    if drvef_table in tables:
        query = f"SELECT UNITID, FTE FROM {drvef_table}"
        fte_df = pd.read_sql_query(query, conn)
        
        for _, row in fte_df.iterrows():
            unitid = row['UNITID']
            if unitid not in data:
                data[unitid] = {'UNITID': unitid, 'Institution Name': None}
            data[unitid][f'{year} - DRVEF - Full-time equivalent fall enrollment'] = row['FTE']
    
    # Get Total Expenses from Finance table
    # Finance tables are named like f2223_f2 for 2023
    prev_year = str(int(year) - 1)
    finance_table = f"f{prev_year[-2:]}{year[-2:]}_f2"
    
    if finance_table in tables:
        query = f"SELECT UNITID, F2E131 FROM {finance_table}"
        expenses_df = pd.read_sql_query(query, conn)
        
        for _, row in expenses_df.iterrows():
            unitid = row['UNITID']
            if unitid not in data:
                data[unitid] = {'UNITID': unitid, 'Institution Name': None}
            data[unitid][f'{year} - F - Total expenses-Total amount'] = row['F2E131']
    
    # Convert to DataFrame
    result_df = pd.DataFrame.from_dict(data, orient='index')
    result_df = result_df.reset_index(drop=True)
    
    # Sort by Institution Name
    result_df = result_df.sort_values('Institution Name').reset_index(drop=True)
    
    return result_df


def get_data_from_csv(csv_filepath):
    """
    Extract FTE and Total Expenses data from a CSV file.
    
    Args:
        csv_filepath (str): Path to the CSV file
        
    Returns:
        tuple: (year, pandas.DataFrame) Year string and DataFrame with data
    """
    # Extract year from filename
    filename = os.path.basename(csv_filepath)
    year_str = filename.split('-')[-1].replace('.csv', '')
    
    # Read the CSV
    df = pd.read_csv(csv_filepath)
    
    # Standardize column names
    # Expected columns: UnitID, Institution Name, Total expenses-Total amount (F2324_F2), Full-time equivalent fall enrollment (DRVEF2024)
    
    # Find the columns (they may have slightly different names)
    unitid_col = None
    name_col = None
    expenses_col = None
    fte_col = None
    
    for col in df.columns:
        col_lower = col.lower()
        if 'unitid' in col_lower or col == 'UnitID':
            unitid_col = col
        elif 'institution name' in col_lower:
            name_col = col
        elif 'total expenses' in col_lower or 'f2e' in col_lower:
            expenses_col = col
        elif 'full-time equivalent' in col_lower or 'drvef' in col_lower:
            fte_col = col
    
    if not all([unitid_col, expenses_col, fte_col]):
        raise ValueError(f"Could not find required columns in {csv_filepath}")
    
    # Create result DataFrame
    result_df = pd.DataFrame()
    result_df['UNITID'] = df[unitid_col]
    
    if name_col:
        result_df['Institution Name'] = df[name_col]
    else:
        result_df['Institution Name'] = None
    
    result_df[f'{year_str} - F - Total expenses-Total amount'] = df[expenses_col]
    result_df[f'{year_str} - DRVEF - Full-time equivalent fall enrollment'] = df[fte_col]
    
    # Sort by Institution Name
    result_df = result_df.sort_values('Institution Name').reset_index(drop=True)
    
    return year_str, result_df


def generate_combined_report(conn, csv_files):
    """
    Generate a combined report with all years.
    
    Args:
        conn: SQLite database connection (may be None)
        csv_files (dict): Dictionary mapping year to CSV filepath
        
    Returns:
        pandas.DataFrame: Combined report with all years
    """
    print(f"\n{'='*70}")
    print("Generating Combined Report")
    print(f"{'='*70}")
    
    # Get available years from database
    db_years = get_available_years_from_db(conn) if conn else []
    
    # Get available years from CSV files
    csv_years = sorted(csv_files.keys())
    
    # Combine all years
    all_years = sorted(set(db_years + csv_years))
    
    print(f"\nData sources:")
    print(f"  Database years: {db_years if db_years else 'None'}")
    print(f"  CSV years: {csv_years if csv_years else 'None'}")
    print(f"  Total years: {all_years}")
    
    # Start with institution list
    result_df = None
    
    # Process each year
    for year in all_years:
        print(f"\nProcessing year {year}...")
        
        year_df = None
        
        # Prefer CSV data if available (it's the most recent/authoritative)
        if year in csv_files:
            print(f"  Using CSV: {os.path.basename(csv_files[year])}")
            _, year_df = get_data_from_csv(csv_files[year])
        
        # Otherwise use database
        elif conn and year in db_years:
            print(f"  Using database")
            year_df = get_data_from_db(conn, year)
        
        if year_df is None:
            print(f"  ⚠ No data found for year {year}")
            continue
        
        # Merge with result
        if result_df is None:
            result_df = year_df
        else:
            # Merge on UNITID
            result_df = result_df.merge(
                year_df, 
                on='UNITID', 
                how='outer',
                suffixes=('', '_dup')
            )
            
            # Handle duplicate Institution Name column
            if 'Institution Name_dup' in result_df.columns:
                # Use non-null values from either column
                result_df['Institution Name'] = result_df['Institution Name'].fillna(
                    result_df['Institution Name_dup']
                )
                result_df = result_df.drop(columns=['Institution Name_dup'])
        
        print(f"  ✓ Added {len(year_df)} institutions")
    
    if result_df is None:
        print("\n✗ No data available to generate report")
        return None
    
    # Reorder columns: UNITID, Institution Name, then years in chronological order
    cols = ['UNITID', 'Institution Name']
    
    # Add year columns in order
    for year in all_years:
        for col in result_df.columns:
            if col.startswith(year) and col not in cols:
                cols.append(col)
    
    result_df = result_df[cols]
    
    # Sort by Institution Name
    result_df = result_df.sort_values('Institution Name').reset_index(drop=True)
    
    print(f"\n✓ Combined report: {len(result_df)} institutions × {len(result_df.columns)} columns")
    
    return result_df


def generate_year_reports(conn, csv_files):
    """
    Generate separate reports for each year.
    
    Args:
        conn: SQLite database connection (may be None)
        csv_files (dict): Dictionary mapping year to CSV filepath
        
    Returns:
        dict: Dictionary mapping year to DataFrame
    """
    print(f"\n{'='*70}")
    print("Generating Year-Specific Reports")
    print(f"{'='*70}")
    
    # Get available years
    db_years = get_available_years_from_db(conn) if conn else []
    csv_years = sorted(csv_files.keys())
    all_years = sorted(set(db_years + csv_years))
    
    year_reports = {}
    
    for year in all_years:
        print(f"\nYear {year}...")
        
        year_df = None
        
        # Prefer CSV data if available
        if year in csv_files:
            print(f"  Using CSV: {os.path.basename(csv_files[year])}")
            _, year_df = get_data_from_csv(csv_files[year])
        
        # Otherwise use database
        elif conn and year in db_years:
            print(f"  Using database")
            year_df = get_data_from_db(conn, year)
        
        if year_df is None:
            print(f"  ⚠ No data found")
            continue
        
        # Rename columns to remove year prefix (since it's in the filename)
        # Example: "2023 - F - Total expenses-Total amount" -> "F - Total expenses-Total amount"
        rename_map = {}
        for col in year_df.columns:
            if col.startswith(year):
                new_name = col.replace(f'{year} - ', '')
                rename_map[col] = new_name
        
        year_df = year_df.rename(columns=rename_map)
        
        year_reports[year] = year_df
        print(f"  ✓ {len(year_df)} institutions × {len(year_df.columns)} columns")
    
    return year_reports


def save_reports(combined_df=None, year_reports=None, output_dir=None):
    """
    Save reports to Excel files.
    
    Args:
        combined_df (DataFrame): Combined report across all years
        year_reports (dict): Dictionary of year-specific reports
        output_dir (str): Directory to save files (default: current directory)
        
    Returns:
        list: List of saved filenames
    """
    if output_dir is None:
        output_dir = os.getcwd()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"\n{'='*70}")
    print("Saving Reports")
    print(f"{'='*70}")
    
    saved_files = []
    
    # Save combined report
    if combined_df is not None:
        filename = os.path.join(output_dir, f"ACA_Member_FTE_Expenses_Combined_{timestamp}.xlsx")
        combined_df.to_excel(filename, index=False)
        print(f"✓ Saved combined report: {filename}")
        saved_files.append(filename)
    
    # Save year-specific reports
    if year_reports:
        for year, df in year_reports.items():
            filename = os.path.join(output_dir, f"ACA_Member_FTE_Expenses_{year}_{timestamp}.xlsx")
            df.to_excel(filename, index=False)
            print(f"✓ Saved {year} report: {filename}")
            saved_files.append(filename)
    
    return saved_files


def print_summary(conn, csv_files):
    """
    Print a summary of available data sources.
    
    Args:
        conn: SQLite database connection (may be None)
        csv_files (dict): Dictionary mapping year to CSV filepath
    """
    print(f"\n{'='*70}")
    print("Data Source Summary")
    print(f"{'='*70}")
    
    # Database info
    if conn:
        db_years = get_available_years_from_db(conn)
        print(f"\nSQLite Database ({DB_PATH}):")
        print(f"  Available years: {', '.join(db_years) if db_years else 'None'}")
    else:
        print(f"\nSQLite Database ({DB_PATH}): Not found")
    
    # CSV files info
    print(f"\nCSV Files:")
    if csv_files:
        for year, filepath in sorted(csv_files.items()):
            print(f"  {year}: {os.path.basename(filepath)}")
    else:
        print(f"  No CSV files found matching pattern: {CSV_PATTERN}")
    
    # All available years
    db_years = get_available_years_from_db(conn) if conn else []
    csv_years = sorted(csv_files.keys())
    all_years = sorted(set(db_years + csv_years))
    
    print(f"\nTotal years available: {', '.join(all_years) if all_years else 'None'}")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main function to generate reports."""
    
    print("="*70)
    print("ACA Library FTE and Expenses Report Generator")
    print("="*70)
    
    # Connect to database (if it exists)
    conn = get_database_connection()
    
    # Find CSV files
    csv_files = find_csv_files()
    
    # Print summary
    print_summary(conn, csv_files)
    
    # Check if we have any data
    db_years = get_available_years_from_db(conn) if conn else []
    if not db_years and not csv_files:
        print("\n✗ Error: No data sources found")
        print("Please ensure:")
        print(f"  1. {DB_PATH} exists with data, OR")
        print(f"  2. CSV files matching '{CSV_PATTERN}' exist in the current directory")
        if conn:
            conn.close()
        return
    
    # Ask user what type of report they want
    print(f"\n{'='*70}")
    print("Report Options")
    print(f"{'='*70}")
    print("1. Combined report (all years in one file)")
    print("2. Separate reports by year")
    print("3. Both")
    
    choice = input("\nEnter your choice (1/2/3): ").strip()
    
    combined_df = None
    year_reports = None
    
    if choice in ['1', '3']:
        combined_df = generate_combined_report(conn, csv_files)
    
    if choice in ['2', '3']:
        year_reports = generate_year_reports(conn, csv_files)
    
    # Save reports
    if combined_df is not None or year_reports is not None:
        saved_files = save_reports(combined_df, year_reports)
        
        print(f"\n{'='*70}")
        print("Report Generation Complete!")
        print(f"{'='*70}")
        print(f"\nGenerated {len(saved_files)} file(s):")
        for f in saved_files:
            print(f"  • {os.path.basename(f)}")
        
        print(f"\nNext steps:")
        print("  1. Review the Excel files to ensure data looks correct")
        print("  2. Share with committee or upload to Airtable as needed")
    else:
        print("\n✗ No reports generated")
    
    # Close database connection
    if conn:
        conn.close()


if __name__ == "__main__":
    main()
