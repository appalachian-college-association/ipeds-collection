# BCLA Library Data Import Workflow

This workflow processes IPEDS .accdb files (2019-2024) to create a SQLite database with Academic Libraries and Fall Enrollment data for BCLA member institutions.

## Overview

The workflow consists of four Python scripts that work together:

1. **bcla_library_import.py** - Extracts data from .accdb files into SQLite
2. **bcla_variable_titles.py** - Adds user-friendly column names from Excel documentation
3. **bcla_report_generator.py** - Creates Excel reports for Academic Libraries data for BCLA member libraries
4. **aca_fte_expenses_report.py** - Creates Excel report with FTE and F2 (total expenses) for BCLA member libraries

## Files You Need

Before running the scripts, make sure you have these files in your project directory:

### IPEDS .accdb files (5 files):
- `IPEDS201920.accdb` (2019-20 academic year)
- `IPEDS202021.accdb` (2020-21 academic year)
- `IPEDS202122.accdb` (2021-22 academic year)
- `IPEDS202223.accdb` (2022-23 academic year)
- `IPEDS202324.accdb` (2023-24 academic year)

### IPEDS Excel documentation files (5 files):
- `IPEDS201920tablesdoc.xlsx`
- `IPEDS202021tablesdoc.xlsx`
- `IPEDS202122tablesdoc.xlsx`
- `IPEDS202223tablesdoc.xlsx`
- `IPEDS202324tablesdoc.xlsx`

These files are available for download from IPEDS:
https://nces.ed.gov/ipeds/use-the-data/download-access-database (last accessed 1/30/2026)

## Required Python Packages

Install the required packages using these commands in your terminal:

```bash
pip install pandas
pip install pyodbc
pip install openpyxl
```

**Note about pyodbc:** This package requires the Microsoft Access Database Engine. On Windows, this is usually already installed. If you get errors about missing drivers, you may need to install the Microsoft Access Database Engine Redistributable.

## Step-by-Step Instructions

### Step 1: Extract Data from .accdb Files

Run the main import script:

```bash
python bcla_library_import.py
```

**What this does:**
- Connects to each .accdb file
- Extracts five types of tables for each year:
  - DRVEF (Fall Enrollment - contains FTE variable)
  - F (Financial - contains Total expenses variable)
  - AL (Academic Libraries - 37 variables)
  - DRVAL (Derived Academic Library Variables - 19 variables)
  - HD (Directory information - institution names)
- Filters to only BCLA institutions (34 institutions -- JUF included as separate row)
- Saves all data to `bcla_library.sqlite`

**What to expect:**
- The script will process each year and show progress
- It will ask to confirm if you want to overwrite an existing database
- At the end, you'll see a verification showing all tables created

**Estimated time:** 2-5 minutes depending on your computer

### Step 2: Import Variable Titles

Run the variable titles script:

```bash
python bcla_variable_titles.py
```

**What this does:**
- Reads the 'vartable' sheets from each Excel documentation file
- Creates a lookup table that maps variable codes (like 'FTE', 'LEXPTOT') to readable names (like 'Full-time equivalent fall enrollment', 'Total library expenditures')
- Tracks if variable titles changed between years
- Adds the `variable_titles` table to your database

**What to expect:**
- The script will read each Excel file and show progress
- At the end, you'll see a sample of variable mappings
- If any variable titles changed between years, you'll see a count

**Estimated time:** Less than 1 minute

### Step 3: Generate Reports

Run the report generators:

```bash
python bcla_report_generator.py
python aca_fte_expenses_report.py
```

**What this does:**
- Shows a summary of data availability
- Asks what type of report you want:
  - **Option 1:** Combined report (all years in one Excel file)
  - **Option 2:** Separate reports by year (one Excel file per year)
  - **Option 3:** Both
- Creates Excel files with user-friendly column names

**What to expect:**
- You'll see a data availability summary
- You'll be prompted to choose a report type
- Excel files will be created in your current directory with timestamps

**Estimated time:** 1-3 minutes depending on report type

## Output Files

After running all four scripts, you'll have:

1. **bcla_library.sqlite** - Your SQLite database with all the data
2. **BCLA_Library_Combined_YYYYMMDD_HHMMSS.xlsx** - Combined report (if you chose option 1 or 3)
3. **BCLA_Library_2019_YYYYMMDD_HHMMSS.xlsx** through **BCLA_Library_2023_YYYYMMDD_HHMMSS.xlsx** - Year-specific reports (if you chose option 2 or 3)
4. **ACA_Member_FTE_Expenses_Combined_YYYYMMDD_HHMMSS.xlsx** - Combined report (if you chose option 1 or 3)
3. **ACA_Member_FTE_2019_YYYYMMDD_HHMMSS.xlsx** through **BCLA_Library_2023_YYYYMMDD_HHMMSS.xlsx** - Year-specific reports (if you chose option 2 or 3)


The timestamp (YYYYMMDD_HHMMSS) ensures files don't overwrite each other when you run the script multiple times.

## Understanding the Data Structure

### Tables in the Database

Your SQLite database will contain these tables:

**Data Tables (3 per year × 5 years = 15 tables):**
- `drvef2019` through `drvef2023` - Fall Enrollment with FTE variable
- `al2019` through `al2023` - Academic Libraries data (37 variables)
- `drval2019` through `drval2023` - Derived Academic Library Variables (19 variables)
- 'f1819_f2' through 'f2223_f2' - Total Expenses with F2E131 variable

**Institution Tables (5 tables):**
- `hd2019` through `hd2023` - Institution names and IDs

**Lookup Tables (2 tables):**
- `variable_titles` - Maps variable codes to readable names
- `variable_titles_lookup` - View for easy access

### Excel Report Column Names

Column names in the Excel reports follow this pattern:
- **Combined report:** `Year - TableType - Variable Title`
  - Example: `2023 - AL - Total library expenditures`
- **Year-specific reports:** `TableType - Variable Title`
  - Example: `AL - Total library expenditures`

## Troubleshooting

### "Database not found" error
- Make sure you run the scripts in order (import → variable titles → report generator)
- Check that you're in the correct directory

### "File not found" error for .accdb files
- Make sure all .accdb files are in the same directory as the script
- Check that filenames match exactly (case-sensitive on some systems)

### "No variable mappings loaded" error
- Check that Excel documentation files are in the same directory
- Verify that the files contain a sheet named 'vartableXX' (where XX is the year)

### pyodbc driver errors
- On Windows: Install Microsoft Access Database Engine Redistributable
- Download from: https://www.microsoft.com/en-us/download/details.aspx?id=54920
- Make sure to install the version (32-bit or 64-bit) that matches your Python installation

## Customization

### Changing Institution List

If you need to add or remove institutions, edit the `BCLA_UNITIDS` list in `bcla_library_import.py`:

```python
BCLA_UNITIDS = [
    156189,  # Alice Lloyd College
    156295,  # Berea College
    # ... add or remove institution IDs here
]
```

### Changing Years

If you need to process different years, edit the `YEARS` list in `bcla_library_import.py`:

```python
YEARS = [2019, 2020, 2021, 2022, 2023]  # Modify as needed
```

Also update `FILE_MAPPINGS` in `bcla_variable_titles.py` to match.

## Version Control with Git

When you're ready to save your work to GitHub:

1. **Initialize repository (first time only):**
   ```bash
   git init
   git add bcla_library_import.py bcla_variable_titles.py bcla_report_generator.py README.md
   git commit -m "Initial commit: BCLA library data import scripts"
   ```

2. **Create .gitignore file:**
   Create a file named `.gitignore` with these contents:
   ```
   # Ignore data files
   *.accdb
   *.sqlite
   *.xlsx
   
   # Ignore Python cache
   __pycache__/
   *.pyc
   ```

3. **Push to GitHub:**
   ```bash
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

4. **Save changes as you work:**
   ```bash
   git add .
   git commit -m "Descriptive message about what you changed"
   git push
   ```

## Next Steps for Your Project

After generating the reports:

1. **Review the data** - Open the Excel files and verify the data looks correct
2. **Check for missing data** - Some institutions may not have reported certain variables in certain years
3. **Prepare for committee** - Use the Excel reports to create your presentation
4. **Document definitions** - The variable titles table has the official IPEDS definitions
5. **Plan Airtable migration** - Once committee approves, you can import the Excel files to Airtable

## Questions or Issues?

If you encounter problems:
1. Check the error messages - they often tell you exactly what's wrong
2. Verify all required files are in place
3. Make sure you ran the scripts in order
4. Check that Python packages are installed correctly

## Script Descriptions

### bcla_library_import.py
The main workhorse script. It:
- Uses the `pyodbc` library to connect to Microsoft Access databases
- Loops through each year (2019-2023)
- For each year, extracts the needed tables (DRVEF, AL, DRVAL, HD)
- Filters each table to only BCLA institutions
- Saves everything to a SQLite database

**Key functions:**
- `connect_to_accdb()` - Creates connection to .accdb file
- `get_table_from_accdb()` - Extracts a table and filters by institution
- `process_year()` - Processes all tables for one year
- `save_to_sqlite()` - Saves all data to database

### bcla_variable_titles.py
Creates readable column names. It:
- Reads the 'vartable' sheets from Excel documentation
- Combines variable titles across all years
- Identifies if titles changed between years
- Creates a lookup table in the database

**Key functions:**
- `read_variable_mappings()` - Reads Excel files
- `create_consolidated_variables_table()` - Combines all years
- `save_to_sqlite()` - Saves to database

### bcla_report_generator.py
Creates Excel reports. It:
- Reads data from the SQLite database
- Looks up user-friendly names for variables
- Combines data from multiple tables
- Creates Excel files with your data

**Key functions:**
- `generate_combined_report()` - Creates one file with all years
- `generate_year_reports()` - Creates one file per year
- `save_reports()` - Writes Excel files

### aca_fte_expenses_report.py
Creates simplified Excel reports with just FTE enrollment and Total Expenses. It reads data from:
- Historical years (2019-2023): SQLite database (bcla_library.sqlite)
- Most recent year: CSV export from IPEDS Data Center (aca-ipeds-fte-f2e131-{year}.csv)

- Looks up user-friendly names for variables
- Combines data from multiple tables
- Creates Excel files with your data

**Key functions:**
- `generate_combined_report()` - Creates one file with all years
- `generate_year_reports()` - Creates one file per year
- `save_reports()` - Writes Excel files
