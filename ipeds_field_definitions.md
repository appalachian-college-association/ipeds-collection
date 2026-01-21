# IPEDS Field Definitions for BCLA Consortium

## Overview
This document provides detailed definitions for the IPEDS (Integrated Postsecondary Education Data System) data fields collected for BCLA member institutions. This data is sourced from the Education Data Portal API maintained by the Urban Institute.

**Data Coverage**: Academic years 2013-2024  
**Source**: IPEDS via Education Data Portal (https://educationdata.urban.org/)  
**Last Updated**: January 2025

---

## Core Identification Fields

### unitid
- **Definition**: IPEDS Unit Identification Number
- **Type**: Integer (6 digits)
- **Purpose**: Unique identifier assigned by IPEDS to each postsecondary institution
- **Example**: 156189 (Alice Lloyd College)
- **Notes**: This number remains constant for an institution across all years

### year
- **Definition**: Academic Year
- **Type**: Integer (4 digits)
- **Format**: The ending year of the academic cycle
- **Example**: 2024 represents the 2023-2024 academic year
- **Notes**: IPEDS data is reported annually, typically in the fall following the academic year

---

## Academic Libraries Data
*Source: IPEDS Academic Libraries Component*

### total_expenses
- **Full Name**: Total Library Expenses
- **IPEDS Variable**: F2223_F2 (varies by year)
- **Definition**: The sum of all operating expenses for the academic library
- **Type**: Currency (USD)
- **Includes**:
  - Salaries and wages for all library staff
  - Employee benefits
  - Materials and supplies (including collections)
  - Contract services
  - Equipment
  - Other operating expenses
- **Excludes**:
  - Capital expenditures (buildings, major renovations)
  - Debt service
  - Auxiliary enterprises
- **Reporting Period**: Fiscal year (varies by institution)
- **Use Cases**:
  - Benchmarking library budgets across institutions
  - Tracking expense trends over time
  - Calculating per-FTE library spending
- **Important Notes**:
  - Expenses may reflect different fiscal year periods depending on institutional calendars
  - Some institutions may not report if they don't meet IPEDS Academic Libraries criteria
  - Data may be unavailable for institutions with libraries below reporting thresholds

### database_count
- **Full Name**: Number of Licensed Databases
- **IPEDS Variable**: LDBS (varies by year)
- **Definition**: Total number of licensed electronic databases available to library users
- **Type**: Integer
- **Includes**:
  - Subscription databases
  - Aggregated full-text databases
  - Bibliographic databases
  - E-journal collections counted as databases
- **Excludes**:
  - Individual e-journals not part of a database
  - Free/open access databases (in some reporting years)
  - Locally created databases
- **Use Cases**:
  - Comparing digital resource investments across institutions
  - Tracking growth in electronic resource access
  - Assessing diversity of information resources
- **Important Notes**:
  - Counting methodologies may vary between institutions
  - The definition of "database" has evolved over the reporting period
  - Package deals may be counted differently by different institutions

---

## Fall Enrollment Data
*Source: IPEDS Fall Enrollment Component*

### fte
- **Full Name**: Full-Time Equivalent Student Enrollment
- **IPEDS Variable**: EFYTOTLT or FTE_TOTAL (varies by year)
- **Definition**: A single value providing a meaningful combination of full-time and part-time students
- **Type**: Decimal number
- **Calculation Method**:
  - Full-time students count as 1.0 each
  - Part-time students typically count as 0.333333 each (1/3)
  - Formula: FTE = Full-time students + (Part-time students × 0.333333)
- **Enrollment Type**: Fall enrollment snapshot
- **Reporting Period**: Fall census date (typically October)
- **Includes**:
  - Undergraduate students (full and part-time)
  - Graduate students (full and part-time)
  - Professional students (full and part-time)
- **Excludes**:
  - Students in non-credit programs
  - Continuing education students (unless credit-seeking)
  - Students exclusively in distance education (in some years)
- **Use Cases**:
  - Calculating per-FTE library metrics (expenses, database count)
  - Comparing institutional size
  - Normalizing data for meaningful comparisons
  - Accreditation reporting
- **Important Notes**:
  - The part-time multiplier (0.333333) is standard across IPEDS reporting
  - FTE is a snapshot at one point in time, not an annual average
  - Some institutions may have significantly different fall vs. spring enrollment

---

## Calculated Metrics (You Can Create These in Airtable)

### Per-FTE Library Expenses
- **Formula**: total_expenses ÷ fte
- **Type**: Currency (USD)
- **Purpose**: Normalizes library spending across institutions of different sizes
- **Interpretation**: Higher values indicate greater per-student library investment

### Databases per 1,000 FTE
- **Formula**: (database_count ÷ fte) × 1000
- **Type**: Decimal
- **Purpose**: Normalizes database access across institutions of different sizes
- **Interpretation**: Shows relative richness of database offerings per student population

---

## Data Quality and Completeness

### Missing Data
**Why data might be missing**:
- Institution didn't meet reporting threshold for Academic Libraries component
- Institution didn't respond to specific IPEDS survey sections
- Data not yet available for most recent year
- Institution reporting exemption or delay

### Data Accuracy
**Quality considerations**:
- IPEDS data is self-reported by institutions
- Definitions and counting methods can vary slightly between institutions
- Data is reviewed by IPEDS but not audited
- Corrections and revisions may be made in subsequent years

### Comparability Across Years
**Important notes**:
- IPEDS occasionally revises survey questions and definitions
- Institution mergers, closures, or status changes can affect comparability
- Changes in institutional fiscal years can create apparent anomalies
- Inflation should be considered when comparing expenses across years

---

## Using This Data Effectively

### Best Practices
1. **Compare within similar institution types** (size, Carnegie classification, etc.)
2. **Look at trends over multiple years** rather than single-year snapshots
3. **Consider institutional context** (e.g., a medical school library vs. liberal arts library)
4. **Use per-FTE calculations** for meaningful size-normalized comparisons
5. **Account for inflation** when comparing expenses across multiple years

### Benchmarking Suggestions
- Compare your institution to peer institutions of similar size
- Track your own trends over time
- Calculate consortial averages and medians
- Identify outliers and investigate reasons
- Use data to inform budget requests and strategic planning

### Questions to Ask
- How do our library expenses compare to similar institutions?
- Are our database offerings keeping pace with student enrollment growth?
- What trends do we see in library investment across the consortium?
- How has per-FTE spending changed over the past 5 years?

---

## Additional Resources

### IPEDS Resources
- **IPEDS Homepage**: https://nces.ed.gov/ipeds/
- **IPEDS Glossary**: https://surveys.nces.ed.gov/ipeds/VisGlossaryAll.aspx
- **Academic Libraries Survey Forms**: Available on IPEDS website
- **IPEDS Data Center**: https://nces.ed.gov/ipeds/datacenter/

### Education Data Portal
- **Homepage**: https://educationdata.urban.org/
- **API Documentation**: https://educationdata.urban.org/documentation/
- **Data Dictionary**: Available for each endpoint

### Professional Organizations
- **ACRL Metrics**: https://www.ala.org/acrl/ (Association of College & Research Libraries)
- **NISO**: https://www.niso.org/ (Standards for library data)

---

## Technical Notes

### API Source Information
- **Provider**: Urban Institute Education Data Portal
- **Endpoints Used**:
  - Academic Libraries: `/api/v1/college-university/ipeds/academic-libraries/`
  - Fall Enrollment: `/api/v1/college-university/ipeds/fall-enrollment/`
- **Update Frequency**: Annually, typically 6-12 months after the academic year ends
- **Data Format**: JSON via REST API

### Variable Name Variations
IPEDS variable names may change across years. Common variations:

**Total Expenses**:
- ltotexpn (earlier years)
- total_expenses (recent years)
- F2223_F2 (form-based naming)

**Database Count**:
- ldbs (common variable name)
- database_count (API naming)

**FTE Enrollment**:
- efytotlt (earlier years)
- fte_total (recent years)
- fte (simplified API naming)

---

## Change Log

### Version History
- **v1.0 (January 2025)**: Initial documentation created for BCLA consortium
  - Coverage: 2013-2024 academic years
  - Fields: total_expenses, database_count, fte

### Future Updates
This documentation should be reviewed annually when new IPEDS data becomes available. Update as needed when:
- IPEDS changes survey questions or definitions
- New years of data are added
- Additional fields are incorporated into the dataset

---

## Contact Information

**Data Questions**: Contact your BCLA Systems Librarian  
**IPEDS Technical Support**: 1-877-225-2568 or ipedshelp@rti.org  
**Education Data Portal Support**: https://educationdata.urban.org/documentation/

---

## Appendix: BCLA Member Institutions

For reference, the complete list of BCLA member institutions included in this dataset:

1. Alice Lloyd College (156189)
2. Berea College (156295)
3. Bethany College (237181)
4. Bluefield University (231554)
5. Brevard College (198066)
6. Bryan College-Dayton (219790)
7. Campbellsville University (156365)
8. Carson-Newman University (219806)
9. Davis & Elkins College (237358)
10. Emory & Henry University (232025)
11. Ferrum College (232089)
12. Johnson University (220473)
13. Johnson University Florida (132879)
14. Kentucky Christian University (157100)
15. King University (220516)
16. Lee University (220613)
17. Lees-McRae College (198808)
18. Lenoir-Rhyne University (198835)
19. Lincoln Memorial University (220631)
20. Lindsey Wilson College (157216)
21. Mars Hill University (198899)
22. Maryville College (220710)
23. Milligan University (486901)
24. Montreat College (199032)
25. Tennessee Wesleyan University (221731)
26. The University of the South (221519)
27. Tusculum University (221953)
28. Union College (157863)
29. University of Charleston (237312)
30. University of Pikeville (157535)
31. Warren Wilson College (199865)
32. West Virginia Wesleyan College (237969)
33. Wheeling University (238078)
34. Young Harris College (141361)

**Total Institutions**: 34

---

*This documentation is maintained by the BCLA Systems Librarian. Last updated: January 2025*
