# BCLA IPEDS Data Collection Project

## Project Overview
This project collects historical IPEDS (Integrated Postsecondary Education Data System) data for BCLA consortium member institutions using the Education Data Portal API. The collected data will be shared via Airtable for consortium-wide access and analysis.

**Objective**: Create a historical database (2013-present) of key library statistics before IPEDS Academic Libraries data collection ends in 2024-25.

---

## What This Project Does

This automated data collection system:
- ✅ Collects data for 34 BCLA member institutions
- ✅ Covers academic years 2013-2024
- ✅ Gathers 3 key metrics:
  - Total library expenses
  - Database count
  - Fall FTE enrollment
- ✅ Exports to CSV for easy Airtable import
- ✅ Uses the Education Data Portal API (no Access files needed!)

---

## Files Included

### 1. `bcla_ipeds_collector.py`
**Main Python script** that collects the data from the API.

**What it does**:
- Loops through all 34 institutions
- Fetches data for each year from 2013-2024
- Makes API calls to two endpoints (Academic Libraries and Fall Enrollment)
- Exports everything to a CSV file

**Features**:
- Beginner-friendly with extensive comments
- Progress tracking so you can see how it's going
- Error handling to skip missing data gracefully
- Automatic CSV export with timestamp

### 2. `airtable_import_instructions.md`
**Step-by-step guide** for importing your CSV into Airtable.

**Covers**:
- Creating a new Airtable base
- Setting up proper field types
- Adding institution names for readability
- Creating useful views (by year, by institution, etc.)
- Sharing with consortium members
- Common troubleshooting issues

### 3. `ipeds_field_definitions.md`
**Comprehensive documentation** of what each data field means.

**Includes**:
- Official IPEDS definitions
- What's included/excluded in each metric
- How to use the data effectively
- Benchmarking suggestions
- Links to additional IPEDS resources

### 4. `bcla-institutions.txt`
**Reference file** with the 34 BCLA member institution Unit IDs and names.

---

## Prerequisites

### Software Needed
1. **Python 3** (you likely already have this)
   - Check by opening Terminal/Command Prompt and typing: `python --version`
   
2. **Required Python packages**:
   - `requests` (for API calls)
   - `pandas` (for data handling)

### Installing Required Packages

Open your terminal/command prompt and run:

```bash
pip install requests pandas --break-system-packages
```

**Note**: The `--break-system-packages` flag is needed on some systems (like Google Cloud) to install packages.

### What You DON'T Need
❌ Access files - The API provides all necessary data  
❌ SQLite database - This project uses API directly  
❌ Complex setup - Just Python and two packages

---

## How to Run the Script

### Step 1: Prepare Your Environment

1. **Download all project files** to a folder on your computer
2. **Open terminal/command prompt** and navigate to that folder:
   ```bash
   cd /path/to/your/project/folder
   ```

### Step 2: Run the Data Collection Script

Simply type:
```bash
python bcla_ipeds_collector.py
```

### Step 3: Watch the Progress

You'll see output like this:
```
BCLA IPEDS Data Collection Script
======================================================================
Starting data collection for 34 institutions across 12 years...
Total API calls to make: 816 (2 endpoints per year/institution)
----------------------------------------------------------------------

Processing Unit ID: 156189
  Year 2013 (1/408 - 0.2%)
  Year 2014 (2/408 - 0.5%)
  ...
```

**How long will this take?**
- Approximately 6-8 minutes total
- The script waits 0.5 seconds between requests to be polite to the API
- Total requests: ~816 API calls (34 institutions × 12 years × 2 endpoints)

### Step 4: Find Your Output File

When complete, you'll see:
```
Data exported to: bcla_ipeds_data_20250121_143000.csv
Total rows: 408
Columns: unitid, year, total_expenses, database_count, fte, ...
```

The CSV file will be in the same folder where you ran the script.

---

## Understanding the Output

### CSV File Structure

Your CSV will have these columns:

| Column | Description | Example |
|--------|-------------|---------|
| unitid | Institution ID | 156189 |
| year | Academic year | 2024 |
| total_expenses | Library expenses (USD) | 1250000 |
| database_count | Number of databases | 85 |
| fte | Full-time equivalent enrollment | 1234.56 |
| acad_lib_raw | Raw API response (reference) | {...} |
| fall_enroll_raw | Raw API response (reference) | {...} |

### Expected Results

- **Total rows**: 408 (34 institutions × 12 years)
- **Some missing data is normal**: Not all institutions report all data every year
- **Raw data columns**: These contain the full API response for debugging purposes

### Sample Data Check

Open your CSV and verify:
1. You see data for multiple institutions (should be 34 different unitids)
2. Years range from 2013 to 2024
3. Some rows have expenses, database counts, and FTE values
4. Some cells may be blank (this is expected for missing data)

---

## Next Steps

### 1. Review the Data (Recommended)
- Open the CSV in Excel or a text editor
- Spot-check a few familiar institutions
- Look for obvious errors or anomalies

### 2. Import to Airtable
- Follow the instructions in `airtable_import_instructions.md`
- This will guide you through creating a base and setting up views

### 3. Share Documentation
- Send `ipeds_field_definitions.md` to consortium members
- This explains what each field means and how to use the data

### 4. Set Up Regular Updates
Since new IPEDS data comes out annually:
- Run this script again in Fall 2025 for 2024-25 data
- Re-import the updated CSV to Airtable
- Consider setting a calendar reminder

---

## Troubleshooting

### Error: "Module not found: requests"
**Solution**: Install the required package:
```bash
pip install requests --break-system-packages
```

### Error: "Module not found: pandas"
**Solution**: Install the required package:
```bash
pip install pandas --break-system-packages
```

### Error: "Connection timeout" or "API error"
**Possible causes**:
- Internet connection issue
- Education Data Portal API is temporarily down
- Network firewall blocking the API

**Solution**: 
- Check your internet connection
- Wait a few minutes and try again
- If it persists, check https://educationdata.urban.org/ for API status

### All data shows as missing for a specific institution
**This is normal if**:
- The institution is very small (below IPEDS reporting threshold)
- The institution didn't submit data for that year
- The institution's library is integrated into another system

**Solution**: No action needed - document this in your Airtable

### Script is taking a very long time
**Expected runtime**: 6-8 minutes for 816 API calls

**If it's taking much longer**:
- Check your internet connection speed
- The script waits 0.5 seconds between requests (this is intentional)
- You can reduce the wait time by editing line 145: `time.sleep(0.5)` → `time.sleep(0.2)`

---

## Technical Notes

### API Rate Limiting
- The script includes a 0.5 second delay between requests
- This prevents overwhelming the Education Data Portal API
- You can adjust this in the code if needed (line 145)

### Data Persistence
- Each run creates a NEW CSV file with a timestamp
- This prevents accidentally overwriting previous data
- You can safely run the script multiple times

### Field Name Variations
The API may return data in different field names depending on the year:
- Total expenses: `total_expenses`, `ltotexpn`, or `F2223_F2`
- Database count: `database_count` or `ldbs`
- FTE: `fte`, `fte_total`, or `efytotlt`

The script checks for all variations automatically.

---

## Updating the Script for Future Use

### Adding More Years
When 2025 data becomes available (likely Fall 2026):

1. Open `bcla_ipeds_collector.py`
2. Find line 19: `YEARS = list(range(2013, 2025))`
3. Change to: `YEARS = list(range(2013, 2026))`  # Adds 2025
4. Save and run

### Adding/Removing Institutions
If consortium membership changes:

1. Edit the `INSTITUTION_IDS` list (lines 24-58)
2. Add new institution Unit IDs or remove ones that left
3. Update the count on line 102 if needed

### Adding More Data Fields
If you want to collect additional IPEDS fields:

1. Check the Education Data Portal API documentation
2. Find the field name you want
3. Add it to the relevant section in the script (around lines 124-142)
4. The raw data is already being collected, so you can extract new fields from those

---

## Version Control with GitHub (Optional)

Since you're learning GitHub, here's how to track this project:

### Initial Setup
```bash
git init
git add .
git commit -m "Initial commit: BCLA IPEDS data collection project"
```

### After Running the Script
```bash
git add bcla_ipeds_data_*.csv
git commit -m "Collected IPEDS data for 2013-2024"
```

### Recommended .gitignore
Create a `.gitignore` file with:
```
*.csv
__pycache__/
*.pyc
```

This prevents uploading large CSV files to GitHub.

---

## Support and Resources

### IPEDS Resources
- IPEDS Data Center: https://nces.ed.gov/ipeds/datacenter/
- IPEDS Help: ipedshelp@rti.org or 1-877-225-2568

### Education Data Portal Resources
- Homepage: https://educationdata.urban.org/
- API Documentation: https://educationdata.urban.org/documentation/

### Airtable Resources
- Airtable Support: https://support.airtable.com
- Video Tutorials: https://www.youtube.com/c/Airtable

### Python Resources
- Python Beginner's Guide: https://www.python.org/about/gettingstarted/
- Pandas Documentation: https://pandas.pydata.org/docs/

---

## Project Timeline

### Immediate Next Steps (Week 1)
- ✅ Run the data collection script
- ✅ Review CSV output for accuracy
- ✅ Set up Airtable base
- ✅ Import data to Airtable

### Short Term (Month 1)
- Share Airtable with consortium members
- Gather feedback on data usefulness
- Create visualizations in Airtable
- Present at January 2026 committee meeting

### Long Term (Ongoing)
- Annual data updates (Fall each year)
- Consider additional metrics to track
- Develop direct ACA survey for post-2025 data
- Maintain documentation

---

## Questions or Issues?

If you encounter problems or have questions:

1. **Check the Troubleshooting section** above
2. **Review the error message** carefully - it often tells you what's wrong
3. **Verify your Python packages** are installed correctly
4. **Check the Education Data Portal status** at their website
5. **Document the issue** for future reference

Remember: It's okay to experiment! Each run creates a new CSV file with a timestamp, so you can't accidentally lose data by running the script multiple times.

---

## Success Criteria

You'll know the project is successful when:
- ✅ CSV file contains 408 rows (34 institutions × 12 years)
- ✅ Most rows have data in total_expenses, database_count, and fte columns
- ✅ Airtable base is set up and shareable with consortium
- ✅ Consortium members can access and understand the data
- ✅ You have a process for annual updates

---

**Good luck with your data collection! This is a valuable contribution to the BCLA consortium.** 🎉
