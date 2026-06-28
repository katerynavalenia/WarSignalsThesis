import openpyxl
from datetime import datetime

wb = openpyxl.load_workbook(
    r"C:\Users\A00010311\Downloads\Master Thesis\Europe-Central-Asia_aggregated_data_up_to_week_of-2026-06-06.xlsx",
    read_only=True, data_only=True
)
ws = wb.active

# Read all rows
all_rows = []
headers = None
for row in ws.iter_rows(max_row=200000, max_col=20, values_only=True):
    vals = [x for x in row if x is not None]
    if not vals:
        continue
    if headers is None:
        headers = [x for x in row[:20] if x is not None]
        continue
    all_rows.append(row[:len(headers)])
wb.close()

print(f"Headers: {headers}")
print(f"Total data rows: {len(all_rows)}")

# Convert to dataframe for analysis
import pandas as pd
import warnings; warnings.filterwarnings("ignore")

df = pd.DataFrame(all_rows, columns=headers)
print("\ndtypes:", df.dtypes.to_dict())

# Date range
df['WEEK'] = pd.to_datetime(df['WEEK'], errors='coerce')
print(f"\nDate range: {df['WEEK'].min().date()} to {df['WEEK'].max().date()}")

# Country breakdown - focus on Ukraine/Russia
print("\nTop 20 countries by event count:")
print(df.groupby('COUNTRY')['EVENTS'].sum().sort_values(ascending=False).head(20).to_dict())

# Ukraine filter
ukr = df[df['COUNTRY'].str.contains('Ukraine', case=False, na=False)]
print(f"\nUkraine rows: {len(ukr)}")
print("Ukraine event types:")
print(ukr.groupby('EVENT_TYPE')['EVENTS'].sum().sort_values(ascending=False).to_dict())

print("\nSample Ukraine rows (latest):")
print(ukr.sort_values('WEEK', ascending=False).head(5)[['WEEK','COUNTRY','EVENT_TYPE','EVENTS','FATALITIES']].to_string())
