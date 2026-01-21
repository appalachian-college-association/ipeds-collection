"""
BCLA IPEDS Data Collector
This script collects IPEDS data from the Education Data Portal API
for BCLA member institutions from 2013 to present.

Required packages: requests, pandas
Install with: pip install requests pandas --break-system-packages
"""

import requests
import pandas as pd
import time
from datetime import datetime

# ============================================================================
# CONFIGURATION SECTION
# ============================================================================

# Base URL for the Education Data Portal API
BASE_URL = "https://educationdata.urban.org/api/v1/college-university/ipeds"

# Define the years we want to collect (2013 to 2024)
# Note: IPEDS uses academic years, so 2013 = 2012-2013 academic year
YEARS = list(range(2013, 2025))  # This creates [2013, 2014, ..., 2024]

# List of BCLA institution Unit IDs
# This list is from bcla-institutions.txt
INSTITUTION_IDS = [
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
    # 132879,  # Johnson University Florida
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

def fetch_api_data(endpoint, params, description="data"):
    """
    Fetch data from the Education Data Portal API.
    
    Args:
        endpoint (str): The API endpoint path
        params (dict): Parameters to send with the request
        description (str): Description for progress messages
    
    Returns:
        list: The data results from the API, or empty list if error
    """
    url = f"{BASE_URL}/{endpoint}"
    
    try:
        # Make the API request
        # timeout=30 means we'll wait up to 30 seconds for a response
        response = requests.get(url, params=params, timeout=30)
        
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            data = response.json()
            # The API returns data in a 'results' field
            return data.get('results', [])
        else:
            print(f"  Warning: API returned status {response.status_code} for {description}")
            return []
    
    except requests.exceptions.Timeout:
        print(f"  Warning: Request timed out for {description}")
        return []
    
    except requests.exceptions.RequestException as e:
        print(f"  Warning: Error fetching {description}: {str(e)}")
        return []


def fetch_academic_libraries_data(unitid, year):
    """
    Fetch Academic Libraries data for a specific institution and year.
    
    Args:
        unitid (int): The institution's IPEDS Unit ID
        year (int): The year to fetch data for
    
    Returns:
        dict: Dictionary with the data, or None if not found
    """
    endpoint = "academic-libraries"
    params = {
        'unitid': unitid,
        'year': year
    }
    
    results = fetch_api_data(
        endpoint, 
        params, 
        f"Academic Libraries for {unitid} in {year}"
    )
    
    # Return the first result if available
    return results[0] if results else None


def fetch_fall_enrollment_data(unitid, year):
    """
    Fetch Fall Enrollment data for a specific institution and year.
    
    Args:
        unitid (int): The institution's IPEDS Unit ID
        year (int): The year to fetch data for
    
    Returns:
        dict: Dictionary with the data, or None if not found
    """
    endpoint = "fall-enrollment"
    params = {
        'unitid': unitid,
        'year': year
    }
    
    results = fetch_api_data(
        endpoint, 
        params, 
        f"Fall Enrollment for {unitid} in {year}"
    )
    
    # Return the first result if available
    return results[0] if results else None


# ============================================================================
# MAIN DATA COLLECTION FUNCTION
# ============================================================================

def collect_all_data():
    """
    Main function to collect all IPEDS data for all institutions and years.
    
    Returns:
        pandas.DataFrame: DataFrame with all collected data
    """
    # Create an empty list to store all data rows
    all_data = []
    
    # Calculate total operations for progress tracking
    total_operations = len(INSTITUTION_IDS) * len(YEARS)
    current_operation = 0
    
    print(f"Starting data collection for {len(INSTITUTION_IDS)} institutions across {len(YEARS)} years...")
    print(f"Total API calls to make: {total_operations * 2} (2 endpoints per year/institution)")
    print("-" * 70)
    
    # Loop through each institution
    for unitid in INSTITUTION_IDS:
        print(f"\nProcessing Unit ID: {unitid}")
        
        # Loop through each year for this institution
        for year in YEARS:
            current_operation += 1
            progress = (current_operation / total_operations) * 100
            print(f"  Year {year} ({current_operation}/{total_operations} - {progress:.1f}%)")
            
            # Create a dictionary to store this row's data
            row_data = {
                'unitid': unitid,
                'year': year,
            }
            
            # Fetch Academic Libraries data
            acad_lib_data = fetch_academic_libraries_data(unitid, year)
            if acad_lib_data:
                # Extract total expenses (may be in different field names)
                # Common field names: total_expenses, ltotexpn, etc.
                row_data['total_expenses'] = acad_lib_data.get('total_expenses') or acad_lib_data.get('ltotexpn')
                row_data['database_count'] = acad_lib_data.get('database_count') or acad_lib_data.get('ldbs')
                
                # Store the raw data for reference if needed later
                row_data['acad_lib_raw'] = str(acad_lib_data)
            
            # Fetch Fall Enrollment data
            fall_enroll_data = fetch_fall_enrollment_data(unitid, year)
            if fall_enroll_data:
                # Extract FTE - field name might vary (fte, fte_total, etc.)
                row_data['fte'] = fall_enroll_data.get('fte') or fall_enroll_data.get('fte_total') or fall_enroll_data.get('efytotlt')
                
                # Store the raw data for reference
                row_data['fall_enroll_raw'] = str(fall_enroll_data)
            
            # Add this row to our collection
            all_data.append(row_data)
            
            # Be polite to the API - wait a bit between requests
            # This prevents overwhelming the server
            time.sleep(0.5)  # Wait 0.5 seconds between each institution/year combo
    
    print("\n" + "=" * 70)
    print("Data collection complete!")
    print("=" * 70)
    
    # Convert the list of dictionaries to a pandas DataFrame
    df = pd.DataFrame(all_data)
    
    return df


# ============================================================================
# DATA EXPORT FUNCTIONS
# ============================================================================

def export_to_csv(df, filename=None):
    """
    Export the DataFrame to a CSV file.
    
    Args:
        df (pandas.DataFrame): The data to export
        filename (str): Optional custom filename
    """
    if filename is None:
        # Create a filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bcla_ipeds_data_{timestamp}.csv"
    
    # Export to CSV
    # index=False means we don't include the row numbers
    df.to_csv(filename, index=False)
    
    print(f"\nData exported to: {filename}")
    print(f"Total rows: {len(df)}")
    print(f"Columns: {', '.join(df.columns)}")
    
    return filename


def create_summary_report(df):
    """
    Create a summary report of the collected data.
    
    Args:
        df (pandas.DataFrame): The collected data
    """
    print("\n" + "=" * 70)
    print("DATA SUMMARY REPORT")
    print("=" * 70)
    
    # Count how many records we have per year
    print("\nRecords per year:")
    year_counts = df['year'].value_counts().sort_index()
    for year, count in year_counts.items():
        print(f"  {year}: {count} institutions")
    
    # Check for missing data
    print("\nMissing data check:")
    for column in ['total_expenses', 'database_count', 'fte']:
        if column in df.columns:
            missing = df[column].isna().sum()
            percent_missing = (missing / len(df)) * 100
            print(f"  {column}: {missing} missing ({percent_missing:.1f}%)")
    
    # Show a sample of the data
    print("\nSample data (first 5 rows):")
    print(df[['unitid', 'year', 'total_expenses', 'database_count', 'fte']].head())


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("BCLA IPEDS Data Collection Script")
    print("=" * 70)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Collect all the data
    data_df = collect_all_data()
    
    # Step 2: Create a summary report
    create_summary_report(data_df)
    
    # Step 3: Export to CSV
    csv_filename = export_to_csv(data_df)
    
    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nNext steps:")
    print("1. Review the CSV file to ensure data looks correct")
    print("2. Import the CSV into Airtable (instructions provided separately)")
    print("3. Document field definitions for consortium members")
