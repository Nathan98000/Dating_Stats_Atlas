# PUMS 2020-2024 data dictionary verification

Source: https://www2.census.gov/programs-surveys/acs/tech_docs/pums/data_dict/PUMS_Data_Dictionary_2020-2024.csv

Every variable the pipeline relies on, verified programmatically against the
dictionary (pums.py verify). Assertions fail the run if any semantic drifts.

- `SERIALNO`: Housing unit/GQ person serial number
- `SPORDER`: Person number
- `AGEP`: Age
- `SEX`: Sex
- `MSP`: Married, spouse present/spouse absent
- `SCHL`: Educational attainment
- `PINCP`: Total person's income (use ADJINC to adjust to constant dollars)
- `ADJINC`: Adjustment factor for income and earnings dollar amounts (6 implied decimal places)
- `RAC1P`: Recoded detailed race code
- `HISP`: Recoded detailed Hispanic origin
- `RELSHIPP`: Relationship to reference person
- `PWGTP`: Person weight
- `PWGTP1`: Person Weight replicate 1
- `PWGTP80`: Person Weight replicate 80
- `STATE`: State code (NOTE: renamed from `ST` in older vintages)
- `PUMA`: Public use microdata area code (PUMA) based on 2020 Census definition (areas with population of 100,000 or more, use with STATE for unique code) — single column; no PUMA10/PUMA20 in this file
- `RELSHIPP=37`: Institutionalized group quarters population
- `RELSHIPP=38`: Noninstitutionalized group quarters population
- `MSP=b`: N/A (age less than 15 years)
- `MSP=6`: Never married
- `SCHL=15`: 12th grade - no diploma
- `SCHL=16`: Regular high school diploma
- `SCHL=18`: Some college, but less than 1 year
- `SCHL=20`: Associate's degree
- `SCHL=21`: Bachelor's degree
- `SCHL=22`: Master's degree
- `SCHL=24`: Doctorate degree
- `RAC1P=1`: White alone
- `RAC1P=2`: Black or African American alone
- `RAC1P=6`: Asian alone
- `RAC1P=9`: Two or More Races
- `HISP=01`: Not Spanish/Hispanic/Latino
- `SEX=1`: Male
- `SEX=2`: Female
- `ADJINC` factors: 1222017 (2020 factor (1.006149 * 1.21454832)); 1193241 (2021 factor (1.029928 * 1.15856713)); 1117193 (2022 factor (1.042311 * 1.07184241)); 1049470 (2023 factor (1.019518 * 1.02937903)); 1015250 (2024 factor (1.015250 * 1.00000000)); 1222017 (2020 factor (1.006149 * 1.21454832)); 1193241 (2021 factor (1.029928 * 1.15856713)); 1117193 (2022 factor (1.042311 * 1.07184241)); 1049470 (2023 factor (1.019518 * 1.02937903)); 1015250 (2024 factor (1.015250 * 1.00000000))
