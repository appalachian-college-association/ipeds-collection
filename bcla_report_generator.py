"""
BCLA Library Data - Report Generator
This script generates Excel reports from the SQLite database
for presentation to the committee.

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

# SQLite database path
DB_PATH = "bcla_library.sqlite"

# Define which variables to include from each table type
# Format: 'table_prefix': ['varName1', 'varName2', ...]
# Use None or empty list [] to include ALL variables from that table type
VARIABLE_FILTERS = {
    'drvef': ['FTE'],           # Only include FTE from DRVEF tables
    'f': ['F2E131'],            # Only include F2E131 (Total expenses) from Finance tables
    'al': None,                 # Include ALL variables from AL tables
    'drval': None               # Include ALL variables from DRVAL tables
}

# ============================================================================
# FUNCTIONS
# ============================================================================

def get_database_tables(conn):
    """
    Get a list of all tables in the database.
    
    Args:
        conn: SQLite database connection
        
    Returns:
        list: List of table names
    """
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    return tables


def get_column_title(cursor, var_name):
    """
    Get the user-friendly column name from the variable_titles table.
    
    Args:
        cursor: SQLite cursor
        var_name (str): The variable name (e.g., 'FTE', 'LEXPTOT')
        
    Returns:
        str: The user-friendly title, or the original varName if not found
    """
    try:
        cursor.execute(
            "SELECT current_varTitle FROM variable_titles WHERE varName=? LIMIT 1",
            (var_name,)
        )
        result = cursor.fetchone()
        return result[0] if result else var_name
    except:
        # If variable_titles table doesn't exist, just return the varName
        return var_name


def get_table_type(table_name):
    """
    Extract the table type from a table name.
    
    Examples:
        'drvef2019' -> 'drvef'
        'f2223_f2' -> 'f'
        'al2020' -> 'al'
        'drval2021' -> 'drval'
    
    Args:
        table_name (str): The full table name
        
    Returns:
        str: The table type (prefix)
    """
    # Convert to lowercase for comparison
    table_lower = table_name.lower()
    
    # Check each known table type
    for table_type in VARIABLE_FILTERS.keys():
        if table_lower.startswith(table_type):
            return table_type
    
    # If no match, return the alphabetic prefix
    return ''.join(filter(str.isalpha, table_lower))


def should_include_variable(table_name, var_name):
    """
    Determine if a variable should be included in the report based on filters.
    
    Args:
        table_name (str): The table name (e.g., 'drvef2019', 'f2223_f2')
        var_name (str): The variable name (e.g., 'FTE', 'F2E131')
        
    Returns:
        bool: True if the variable should be included
    """
    # Get the table type
    table_type = get_table_type(table_name)
    
    # Check if this table type has filters
    if table_type not in VARIABLE_FILTERS:
        # No filter defined for this table type, include all variables
        return True
    
    # Get the filter for this table type
    filter_list = VARIABLE_FILTERS[table_type]
    
    # If filter is None or empty, include all variables
    if filter_list is None or len(filter_list) == 0:
        return True
    
    # Check if this variable is in the filter list
    return var_name in filter_list


def generate_combined_report(conn):
    """
    Generate a combined report with all years and all variables.
    
    This creates a wide-format table with one row per institution,
    and columns for each variable from each year.
    
    Args:
        conn: SQLite database connection
        
    Returns:
        pandas.DataFrame: The combined report
    """
    cursor = conn.cursor()
    tables = get_database_tables(conn)
    
    # Group tables by type and year
    # We have tables like: drvef2019, drvef2020, al2019, al2020, drval2019, f2223_f2, etc.
    
    # Start with HD tables to get institution names
    hd_tables = [t for t in tables if t.startswith('hd')]
    
    # Use the most recent HD table for institution names
    if hd_tables:
        hd_table = sorted(hd_tables)[-1]
        print(f"Getting institution names from {hd_table}...")
        
        query = f"SELECT UNITID, INSTNM FROM {hd_table}"
        institutions_df = pd.read_sql_query(query, conn)
        institutions_df.columns = ['UNITID', 'Institution Name']
    else:
        print("⚠ Warning: No HD table found, using UNITIDs without names")
        # Get UNITIDs from one of the data tables
        first_table = [t for t in tables if t.startswith(('drvef', 'al', 'drval', 'f'))][0]
        query = f"SELECT DISTINCT UNITID FROM {first_table}"
        institutions_df = pd.read_sql_query(query, conn)
        institutions_df['Institution Name'] = None
    
    # Sort by UNITID for consistent ordering
    institutions_df = institutions_df.sort_values('UNITID').reset_index(drop=True)
    
    print(f"Found {len(institutions_df)} institutions")
    
    # Now process each type of table
    data_tables = [t for t in tables if t.startswith(('drvef', 'al', 'drval', 'f'))]
    
    # Sort tables by year and type
    data_tables.sort()
    
    print(f"\nProcessing {len(data_tables)} data tables...")
    
    # Start with the institutions DataFrame
    result_df = institutions_df.copy()
    
    # Process each data table
    for table in data_tables:
        print(f"  Processing {table}...")
        
        # Read the entire table
        table_df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
        
        # Get year from table name
        # For regular tables like 'drvef2019' -> '2019'
        # For finance tables like 'f2223_f2' -> '2023' (the end year)
        if table.lower().startswith('f'):
            # Finance table - extract year from format like 'f2223_f2'
            year_part = ''.join(filter(str.isdigit, table))[:4]  # Get first 4 digits
            # Convert YYyy to 20yy (e.g., '2223' -> '2023')
            year = '20' + year_part[2:4]
        else:
            year = ''.join(filter(str.isdigit, table))
        
        # Get table type
        table_type = get_table_type(table)
        
        # Count how many variables we'll include
        included_vars = 0
        
        # Merge with result_df on UNITID
        # For each column in table_df (except UNITID), create a new column in result_df
        for col in table_df.columns:
            if col == 'UNITID':
                continue
            
            # Check if this variable should be included
            if not should_include_variable(table, col):
                continue
            
            included_vars += 1
            
            # Get the user-friendly title for this variable
            col_title = get_column_title(cursor, col)
            
            # Create a descriptive column name: "Year - TableType - VariableTitle"
            new_col_name = f"{year} - {table_type.upper()} - {col_title}"
            
            # Merge this column into result_df
            merge_df = table_df[['UNITID', col]].copy()
            merge_df.columns = ['UNITID', new_col_name]
            
            result_df = result_df.merge(merge_df, on='UNITID', how='left')
        
        print(f"    Included {included_vars} variable(s)")
    
    print(f"\n✓ Combined report created: {len(result_df)} rows × {len(result_df.columns)} columns")
    
    return result_df


def generate_year_reports(conn):
    """
    Generate separate reports for each year.
    
    This creates one Excel file per year, with all variables for that year.
    
    Args:
        conn: SQLite database connection
        
    Returns:
        dict: Dictionary with year as key and DataFrame as value
    """
    cursor = conn.cursor()
    tables = get_database_tables(conn)
    
    # Group tables by year
    year_reports = {}
    
    # Extract years from table names
    years = set()
    for table in tables:
        if table.lower().startswith('f'):
            # Finance table like 'f2223_f2'
            year_part = ''.join(filter(str.isdigit, table))[:4]
            year = '20' + year_part[2:4]  # Convert to 2023
            years.add(year)
        else:
            year = ''.join(filter(str.isdigit, table))
            if year and len(year) == 4:
                years.add(year)
    
    years = sorted(years)
    
    print(f"\nGenerating reports for {len(years)} years: {years}")
    
    for year in years:
        print(f"\n  Processing year {year}...")
        
        # Get HD table for institution names
        hd_table = f'hd{year}'
        if hd_table in tables:
            query = f"SELECT UNITID, INSTNM FROM {hd_table}"
            institutions_df = pd.read_sql_query(query, conn)
            institutions_df.columns = ['UNITID', 'Institution Name']
        else:
            # Use any table from this year to get UNITIDs
            year_tables = [t for t in tables if year in t and t.startswith(('drvef', 'al', 'drval', 'f'))]
            if year_tables:
                query = f"SELECT DISTINCT UNITID FROM {year_tables[0]}"
                institutions_df = pd.read_sql_query(query, conn)
                institutions_df['Institution Name'] = None
        
        # Sort by UNITID
        institutions_df = institutions_df.sort_values('UNITID').reset_index(drop=True)
        
        # Start with institutions
        year_df = institutions_df.copy()
        
        # Get all tables for this year
        # For finance tables, need to match differently
        year_tables = []
        for t in tables:
            if t.lower().startswith('f'):
                # Finance table - check if end year matches
                year_part = ''.join(filter(str.isdigit, t))[:4]
                end_year = '20' + year_part[2:4]
                if end_year == year:
                    year_tables.append(t)
            elif year in t and t.startswith(('drvef', 'al', 'drval')):
                year_tables.append(t)
        
        # Process each table
        for table in year_tables:
            print(f"    {table}...")
            
            # Read table
            table_df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
            
            # Get table type
            table_type = get_table_type(table).upper()
            
            # Count included variables
            included_vars = 0
            
            # Merge each column
            for col in table_df.columns:
                if col == 'UNITID':
                    continue
                
                # Check if this variable should be included
                if not should_include_variable(table, col):
                    continue
                
                included_vars += 1
                
                # Get user-friendly title
                col_title = get_column_title(cursor, col)
                
                # Create column name: "TableType - VariableTitle"
                new_col_name = f"{table_type} - {col_title}"
                
                # Merge
                merge_df = table_df[['UNITID', col]].copy()
                merge_df.columns = ['UNITID', new_col_name]
                
                year_df = year_df.merge(merge_df, on='UNITID', how='left')
            
            print(f"      Included {included_vars} variable(s)")
        
        print(f"    ✓ Year {year} report: {len(year_df)} rows × {len(year_df.columns)} columns")
        year_reports[year] = year_df
    
    return year_reports


def save_reports(combined_df=None, year_reports=None, output_dir=None):
    """
    Save reports to Excel files.
    
    Args:
        combined_df (DataFrame): Combined report across all years
        year_reports (dict): Dictionary of year-specific reports
        output_dir (str): Directory to save files (default: current directory)
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
        filename = os.path.join(output_dir, f"BCLA_Library_Combined_{timestamp}.xlsx")
        combined_df.to_excel(filename, index=False)
        print(f"✓ Saved combined report: {filename}")
        saved_files.append(filename)
    
    # Save year-specific reports
    if year_reports:
        for year, df in year_reports.items():
            filename = os.path.join(output_dir, f"BCLA_Library_{year}_{timestamp}.xlsx")
            df.to_excel(filename, index=False)
            print(f"✓ Saved {year} report: {filename}")
            saved_files.append(filename)
    
    return saved_files


def generate_summary_report(conn):
    """
    Generate a summary report showing data availability.
    
    Args:
        conn: SQLite database connection
        
    Returns:
        pandas.DataFrame: Summary report
    """
    print(f"\n{'='*70}")
    print("Data Availability Summary")
    print(f"{'='*70}")
    
    cursor = conn.cursor()
    tables = get_database_tables(conn)
    
    # Get all years
    years = set()
    for table in tables:
        if table.lower().startswith('f'):
            # Finance table
            year_part = ''.join(filter(str.isdigit, table))[:4]
            year = '20' + year_part[2:4]
            years.add(year)
        else:
            year = ''.join(filter(str.isdigit, table))
            if year and len(year) == 4:
                years.add(year)
    
    years = sorted(years)
    
    summary_data = []
    
    for year in years:
        year_data = {'Year': year}
        
        # Check each table type
        for table_type in ['DRVEF', 'AL', 'DRVAL', 'F']:
            # Build expected table name
            if table_type == 'F':
                # Finance table - need to construct the name
                # For year 2023, finance table is f2223_f2
                prev_year = str(int(year) - 1)
                table_name = f"f{prev_year[-2:]}{year[-2:]}_f2"
            else:
                table_name = f"{table_type.lower()}{year}"
            
            if table_name in tables:
                # Count institutions
                query = f"SELECT COUNT(DISTINCT UNITID) as count FROM {table_name}"
                result = pd.read_sql_query(query, conn)
                count = result['count'].iloc[0]
                year_data[table_type] = count
            else:
                year_data[table_type] = 'N/A'
        
        summary_data.append(year_data)
    
    summary_df = pd.DataFrame(summary_data)
    
    print("\nInstitutions per table type and year:")
    print(summary_df.to_string(index=False))
    
    # Show which variables are being included from each table type
    print(f"\n{'='*70}")
    print("Variable Filters Applied")
    print(f"{'='*70}")
    for table_type, filter_list in VARIABLE_FILTERS.items():
        if filter_list is None or len(filter_list) == 0:
            print(f"{table_type.upper()}: All variables included")
        else:
            print(f"{table_type.upper()}: Only including {filter_list}")
    
    return summary_df


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main function to generate reports."""
    
    print("="*70)
    print("BCLA Library Data - Report Generator")
    print("="*70)
    
    # Check if database exists
    if not os.path.exists(DB_PATH):
        print(f"\n✗ Error: Database {DB_PATH} not found")
        print("Please run the import scripts first")
        return
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    
    # Generate summary
    summary_df = generate_summary_report(conn)
    
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
        print(f"\nGenerating combined report...")
        combined_df = generate_combined_report(conn)
    
    if choice in ['2', '3']:
        print(f"\nGenerating year-specific reports...")
        year_reports = generate_year_reports(conn)
    
    # Save reports
    if combined_df is not None or year_reports is not None:
        saved_files = save_reports(combined_df, year_reports)
        
        print(f"\n{'='*70}")
        print("Report Generation Complete!")
        print(f"{'='*70}")
        print(f"\nGenerated {len(saved_files)} file(s):")
        for f in saved_files:
            print(f"  • {os.path.basename(f)}")
    else:
        print("\n✗ No reports generated")
    
    # Close connection
    conn.close()


if __name__ == "__main__":
    main()
