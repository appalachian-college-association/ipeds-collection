# Airtable Import Instructions for BCLA IPEDS Data

## Overview
This guide will walk you through importing your IPEDS data CSV file into Airtable. Airtable is like an enhanced spreadsheet that can store and visualize your data.

---

## Step 1: Prepare Your CSV File

Before importing to Airtable, you should:

1. **Locate your CSV file** - It will be named something like `bcla_ipeds_data_20250121_143000.csv`
2. **Open it in Excel or a text editor** to verify the data looks correct
3. **Check for key columns**: unitid, year, total_expenses, database_count, fte

---

## Step 2: Create a New Airtable Base

1. **Log into Airtable** at https://airtable.com
2. **Click "Add a base"** (you'll see this on your workspace homepage)
3. **Select "Import a spreadsheet"**
4. **Choose "CSV file"**
5. **Upload your CSV file** by dragging and dropping or clicking to browse
6. **Name your base**: Something like "BCLA IPEDS Historical Data"

---

## Step 3: Configure Field Types (IMPORTANT!)

After importing, Airtable will guess what type of data each column contains. You need to verify and adjust these:

### Click on each column header and set the field type:

1. **unitid** 
   - Field type: **Number** (Integer)
   - This is the institution's ID number

2. **year** 
   - Field type: **Number** (Integer)
   - This represents the academic year

3. **total_expenses** 
   - Field type: **Currency** or **Number**
   - If Currency: Choose USD ($)
   - Precision: 2 decimal places
   - This is the total library expenses

4. **database_count** 
   - Field type: **Number** (Integer)
   - Number of databases the library subscribes to

5. **fte** 
   - Field type: **Number** (Decimal)
   - Precision: 2 decimal places
   - This is Full-Time Equivalent enrollment

6. **acad_lib_raw** and **fall_enroll_raw** (optional)
   - Field type: **Long text**
   - These contain the raw API responses for reference
   - You can hide these columns if you don't need them

---

## Step 4: Add a Lookup Column for Institution Names

To make the data more readable, add institution names:

1. **Create a new table** called "Institutions"
2. **Add two columns**:
   - `unitid` (Number)
   - `institution_name` (Single line text)
3. **Manually enter** or copy/paste the institution data from bcla-institutions.txt
4. **Go back to your main data table**
5. **Add a new field** called "Institution"
   - Field type: **Link to another record**
   - Link to: Institutions table
   - Match on: unitid
6. **Add a lookup field** for institution_name
   - This will automatically show the institution name based on the unitid

---

## Step 5: Create Views for Easy Navigation

Views are different ways to look at the same data:

### View 1: By Year
1. Click **"Grid view"** dropdown → **"Create new grid view"**
2. Name it: "By Year"
3. **Group by**: year (descending)
4. **Sort by**: institution_name (A→Z)

### View 2: By Institution
1. Create another new grid view
2. Name it: "By Institution"
3. **Group by**: institution_name
4. **Sort by**: year (descending)

### View 3: Latest Year Only
1. Create another new grid view
2. Name it: "Most Recent Year"
3. **Filter**: Where year = 2024 (or whatever your latest year is)
4. **Sort by**: institution_name (A→Z)

---

## Step 6: Make the Base Shareable (For Consortium Members)

To share with your consortium members:

1. **Click "Share"** button (top right)
2. **Choose sharing option**:
   - **Public read-only link**: Anyone with the link can view but not edit
   - **Invite collaborators**: Add specific email addresses
3. **Set permissions**:
   - **Read only**: They can view but not change data
   - **Comment only**: They can view and add comments
   - **Editor**: They can edit the data (use carefully!)
4. **Copy the share link** to distribute to members

---

## Step 7: Create a Dashboard (Optional)

Airtable has visualization features you can use:

1. **Click "Extensions"** (puzzle piece icon)
2. **Add "Chart" extension**
3. Create visualizations like:
   - Total expenses over time by institution
   - Average FTE across all institutions
   - Database count trends

---

## Common Issues and Solutions

### Issue: Numbers are imported as text
**Solution**: Click the column header → "Customize field type" → Change to Number or Currency

### Issue: Missing data shows as blank
**Solution**: This is normal - not all institutions report all data every year

### Issue: Very large numbers are hard to read
**Solution**: 
- For currency: Use Currency field type with comma separators
- For large numbers: Add a formula field to divide by 1000 and show "in thousands"

### Issue: Can't find unitid for an institution
**Solution**: Check the bcla-institutions.txt file or search IPEDS database directly

---

## Tips for Working with Airtable

1. **Use filters** to focus on specific years or institutions
2. **Hide columns** you don't need (right-click column header → Hide field)
3. **Color-code records** with missing data to track what needs follow-up
4. **Export to Excel** anytime by clicking "..." → "Download CSV"
5. **Set up automations** to notify you when data is updated (advanced feature)

---

## Next Steps After Import

1. **Verify data accuracy** by spot-checking a few institutions
2. **Document any missing data** in a separate table
3. **Create instructions** for consortium members on how to access and use the data
4. **Set up regular updates** - you'll need to run the Python script annually and re-import

---

## Need Help?

- Airtable Support: https://support.airtable.com
- Airtable Community: https://community.airtable.com
- Video tutorials: https://www.youtube.com/c/Airtable

Remember: You can always re-import the data if something goes wrong - Airtable lets you create multiple bases for testing!
