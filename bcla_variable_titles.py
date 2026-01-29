"""
BCLA Library Data - Variable Titles Import
This script imports variable titles from IPEDS Excel documentation files
and creates a lookup table for user-friendly column names.

Required packages: pandas, openpyxl
Install with: pip install pandas openpyxl
"""

import sqlite3
import pandas as pd
import os

# ============================================================================
# CONFIGURATION
# ============================================================================

# SQLite database path (must match the main import script)
DB_PATH = "bcla_library.sqlite"

# Define the mappings between Excel files and years
# You'll need to update these filenames to match your actual files
FILE_MAPPINGS = [
    {
        'file': 'IPEDS201920TablesDoc.xlsx',
        'sheet': 'vartable19',
        'year': '2019'
    },
    {
        'file': 'IPEDS202021TablesDoc.xlsx',
        'sheet': 'vartable20',
        'year': '2020'
    },
    {
        'file': 'IPEDS202122TablesDoc.xlsx',
        'sheet': 'vartable21',
        'year': '2021'
    },
    {
        'file': 'IPEDS202223TablesDoc.xlsx',
        'sheet': 'vartable22',
        'year': '2022'
    },
    {
        'file': 'IPEDS202324TablesDoc.xlsx',
        'sheet': 'vartable23',
        'year': '2023'
    }
]

# ============================================================================
# FUNCTIONS
# ============================================================================

def read_variable_mappings(file_mappings):
    """
    Read variable mappings from Excel documentation files.
    
    This function reads the 'vartable' sheets from IPEDS documentation files.
    These sheets contain the variable names (like 'FTE', 'LEXPTOT') and their
    user-friendly titles (like 'Full-time equivalent fall enrollment').
    
    Args:
        file_mappings (list): List of dictionaries with file info
        
    Returns:
        list: List of DataFrames, one per year
    """
    all_mappings = []
    
    for mapping in file_mappings:
        try:
            file_path = mapping['file']
            sheet_name = mapping['sheet']
            year = mapping['year']
            
            # Check if file exists
            if not os.path.exists(file_path):
                print(f"⚠ Warning: {file_path} not found, skipping year {year}")
                continue
            
            print(f"Reading {file_path}, sheet {sheet_name}...")
            
            # Read the Excel sheet
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            # The sheet should have 'varName' and 'varTitle' columns
            if 'varName' not in df.columns or 'varTitle' not in df.columns:
                print(f"  ⚠ Warning: Required columns not found in {file_path}")
                print(f"  Available columns: {list(df.columns)}")
                continue
            
            # Select only the columns we need
            df = df[['varName', 'varTitle']].copy()
            df['year'] = year
            
            # Remove duplicate varNames within this year (keep first occurrence)
            dup_count = df['varName'].duplicated().sum()
            if dup_count > 0:
                print(f"  Found {dup_count} duplicate varName entries, keeping first occurrence")
                df = df.drop_duplicates(subset=['varName'])
            
            all_mappings.append(df)
            print(f"  ✓ Loaded {len(df)} variable mappings for year {year}")
            
        except Exception as e:
            print(f"  ✗ Error processing {mapping['file']}: {str(e)}")
    
    return all_mappings


def create_consolidated_variables_table(all_mappings):
    """
    Create a consolidated table with variable titles from all years.
    
    This function combines the variable titles from all years and creates
    a single table that shows how variable titles may have changed over time.
    It also selects the most recent title as the 'current' title.
    
    Args:
        all_mappings (list): List of DataFrames from read_variable_mappings
        
    Returns:
        pandas.DataFrame: Consolidated variable titles table
    """
    if not all_mappings:
        print("No mapping data available.")
        return None
    
    # Combine all DataFrames
    combined_df = pd.concat(all_mappings, ignore_index=True)
    
    # Get unique variable names
    all_var_names = combined_df['varName'].unique()
    print(f"\nTotal unique variable names: {len(all_var_names)}")
    
    # Create result DataFrame
    result_data = {
        'varName': all_var_names,
        'id': range(1, len(all_var_names) + 1)
    }
    
    # Add title columns for each year
    for mapping in FILE_MAPPINGS:
        year = mapping['year']
        result_data[f'varTitle_{year}'] = [None] * len(all_var_names)
    
    result_df = pd.DataFrame(result_data)
    
    # Fill in the titles for each year
    for mapping in FILE_MAPPINGS:
        year = mapping['year']
        year_df = combined_df[combined_df['year'] == year]
        
        # Create lookup dictionary
        year_titles = dict(zip(year_df['varName'], year_df['varTitle']))
        
        # Fill in titles
        for idx, row in result_df.iterrows():
            var_name = row['varName']
            if var_name in year_titles:
                result_df.at[idx, f'varTitle_{year}'] = year_titles[var_name]
    
    # Check for variations in titles across years
    def has_variations(row):
        """Check if a variable has different titles in different years."""
        titles = []
        for mapping in FILE_MAPPINGS:
            year = mapping['year']
            title = row.get(f'varTitle_{year}')
            if pd.notnull(title):
                titles.append(title)
        
        # Return True if more than one unique title exists
        return len(set(titles)) > 1 if titles else False
    
    result_df['has_variations'] = result_df.apply(has_variations, axis=1)
    
    # Use the most recent title as the current title
    # Start with the most recent year and work backwards
    years_sorted = sorted([m['year'] for m in FILE_MAPPINGS], reverse=True)
    result_df['current_varTitle'] = None
    
    for year in years_sorted:
        # Fill missing values with this year's title
        result_df['current_varTitle'] = result_df['current_varTitle'].fillna(
            result_df[f'varTitle_{year}']
        )
    
    return result_df


def save_to_sqlite(df, db_path, table_name="variable_titles"):
    """
    Save the variable titles table to SQLite database.
    
    Args:
        df (pandas.DataFrame): The variable titles data
        db_path (str): Path to the SQLite database
        table_name (str): Name for the table
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        
        # Drop table if it exists
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")
        
        # Write the DataFrame to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        
        # Create indexes for faster lookups
        conn.execute(f"CREATE UNIQUE INDEX idx_{table_name}_id ON {table_name} (id)")
        
        # Only create unique index on varName if there are no duplicates
        if not df['varName'].duplicated().any():
            conn.execute(f"CREATE UNIQUE INDEX idx_{table_name}_varName ON {table_name} (varName)")
        
        print(f"✓ Saved {len(df)} rows to {table_name}")
        
        # Create a view for easy lookups
        conn.execute(f"DROP VIEW IF EXISTS {table_name}_lookup")
        conn.execute(f"""
            CREATE VIEW {table_name}_lookup AS
            SELECT varName, current_varTitle
            FROM {table_name}
        """)
        
        print(f"✓ Created view '{table_name}_lookup' for easy lookups")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Error saving to SQLite: {str(e)}")
        return False


def verify_variable_titles(db_path, table_name='variable_titles'):
    """
    Verify the variable titles were saved correctly.
    
    Args:
        db_path (str): Path to the SQLite database
        table_name (str): Name of the variable titles table
    """
    print(f"\n{'='*70}")
    print("Verification")
    print(f"{'='*70}")
    
    conn = sqlite3.connect(db_path)
    
    # Show some sample mappings
    query = f"SELECT varName, current_varTitle FROM {table_name} LIMIT 10"
    sample_df = pd.read_sql_query(query, conn)
    
    print("\nSample variable mappings:")
    for _, row in sample_df.iterrows():
        print(f"  {row['varName']:15} → {row['current_varTitle']}")
    
    # Count total variables
    query = f"SELECT COUNT(*) as count FROM {table_name}"
    count_df = pd.read_sql_query(query, conn)
    total = count_df['count'].iloc[0]
    
    print(f"\nTotal variables in lookup table: {total}")
    
    # Check for variations
    query = f"SELECT COUNT(*) as count FROM {table_name} WHERE has_variations = 1"
    var_df = pd.read_sql_query(query, conn)
    variations = var_df['count'].iloc[0]
    
    if variations > 0:
        print(f"Variables with title changes across years: {variations}")
    
    conn.close()


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main function to run the variable titles import."""
    
    print("="*70)
    print("BCLA Library Data - Variable Titles Import")
    print("="*70)
    
    # Check if database exists
    if not os.path.exists(DB_PATH):
        print(f"\n✗ Error: Database {DB_PATH} not found")
        print("Please run the main import script first")
        return
    
    # Read mappings from Excel files
    print("\nReading variable mappings from Excel files...")
    all_mappings = read_variable_mappings(FILE_MAPPINGS)
    
    if not all_mappings:
        print("\n✗ No variable mappings were loaded")
        print("Please check that the Excel documentation files exist")
        return
    
    # Create consolidated table
    print("\nCreating consolidated variable titles table...")
    variables_df = create_consolidated_variables_table(all_mappings)
    
    if variables_df is not None:
        # Save to SQLite
        save_to_sqlite(variables_df, DB_PATH, "variable_titles")
        
        # Verify the import
        verify_variable_titles(DB_PATH)
        
        print(f"\n{'='*70}")
        print("Variable Titles Import Complete!")
        print(f"{'='*70}")
        print("\nYou can now run the report generator script.")
    else:
        print("\n✗ Failed to create variable titles table")


if __name__ == "__main__":
    main()
