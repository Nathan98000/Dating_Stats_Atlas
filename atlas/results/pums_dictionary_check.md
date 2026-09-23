# PUMS 2020-2024 data dictionary verification (Phase 1)

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
- `MARHYP`: Year last married
- `PWGTP`: Person weight
- `PWGTP1`: Person Weight replicate 1
- `PWGTP80`: Person Weight replicate 80
- `STATE`: State code (renamed from `ST` in older vintages)
- `PUMA`: Public use microdata area code (PUMA) based on 2020 Census definition (areas with population of 100,000 or more, use with STATE for unique code) — single column; no PUMA10/PUMA20
- `RELSHIPP=37`: Institutionalized group quarters population
- `RELSHIPP=38`: Noninstitutionalized group quarters population
- `MSP=b`: N/A (age less than 15 years)
- `MSP=6`: Never married
- `MARHYP`: Year last married -> Phase 3 fitting sample (unions formed since 2019)
- `MARHYP=bbbb`: N/A (age less than 15 years; never married)
- `MARHYP=1945`: 1945 or earlier (Bottom-coded)
- `MARHYP=2024`: 2024
- `RELSHIPP=20..24`: Reference person; Opposite-sex husband/wife/spouse; Opposite-sex unmarried partner; Same-sex husband/wife/spouse; Same-sex unmarried partner
- `SCHL=16`: Regular high school diploma -> hs_or_less
- `SCHL=17`: GED or alternative credential -> hs_or_less
- `SCHL=18`: Some college, but less than 1 year -> some_college
- `SCHL=19`: 1 or more years of college credit, no degree -> some_college
- `SCHL=20`: Associate's degree -> some_college
- `SCHL=21`: Bachelor's degree -> bachelors
- `SCHL=22`: Master's degree -> graduate
- `SCHL=23`: Professional degree beyond a bachelor's degree -> graduate
- `SCHL=24`: Doctorate degree -> graduate
- `PERNP`: Total person's earnings (use ADJINC to adjust to constant dollars) (calibration vs B20001/B20002)
- `ADJINC` factors: 1222017 (2020 factor (1.006149 * 1.21454832)); 1193241 (2021 factor (1.029928 * 1.15856713)); 1117193 (2022 factor (1.042311 * 1.07184241)); 1049470 (2023 factor (1.019518 * 1.02937903)); 1015250 (2024 factor (1.015250 * 1.00000000)); 1222017 (2020 factor (1.006149 * 1.21454832)); 1193241 (2021 factor (1.029928 * 1.15856713)); 1117193 (2022 factor (1.042311 * 1.07184241)); 1049470 (2023 factor (1.019518 * 1.02937903)); 1015250 (2024 factor (1.015250 * 1.00000000))
- income bands (2024 dollars): <25k / 25-50 / 50-75 / 75-100 / 100-150 / 150-250 / >=250k applied to PINCP*ADJINC
- `RAC1P=1`: White alone
- `RAC1P=2`: Black or African American alone
- `RAC1P=6`: Asian alone
- `RAC1P=9`: Two or More Races
- `HISP=01`: Not Spanish/Hispanic/Latino
- `SEX=1`: Male
- `SEX=2`: Female
- `HINCP`: Household income (past 12 months, use ADJINC to adjust HINCP to constant dollars)
- `WGTP`: Housing Unit Weight + WGTP1..WGTP80 replicates
- `TYPEHUGQ=1`: Housing unit
