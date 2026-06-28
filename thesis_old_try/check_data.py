import pandas as pd

# === DAILY GPR ===
path = r'C:\Users\A00010311\Downloads\Master Thesis\data_gpr_daily_recent.xls'
df = pd.read_excel(path)
df['date'] = pd.to_datetime(df['date'], errors='coerce')
valid = df.dropna(subset=['date'])
print('=== DAILY GPR ===')
print('Rows:', len(valid))
print('Date range:', valid['date'].min().date(), 'to', valid['date'].max().date())
print('Columns:', df.columns.tolist())
recent = valid[valid['date'] >= '2020-01-01']
print('Rows from 2020:', len(recent))
print('Invasion period sample (Feb-Mar 2022):')
inv = recent[recent['date'].between('2022-02-20', '2022-03-05')]
print(inv[['date', 'GPRD', 'GPRD_ACT', 'GPRD_THREAT']].to_string())

# === MONTHLY GPR ===
print()
path2 = r'C:\Users\A00010311\Downloads\Master Thesis\data_gpr_export.xls'
df2 = pd.read_excel(path2)
df2['month'] = pd.to_datetime(df2['month'], errors='coerce')
valid2 = df2.dropna(subset=['month'])
print('=== MONTHLY GPR ===')
print('Date range:', valid2['month'].min().date(), 'to', valid2['month'].max().date())
print('Ukraine + Russia GPR (2025 onward):')
tail = valid2[valid2['month'] >= '2025-01-01'][['month', 'GPR', 'GPRC_UKR', 'GPRC_RUS', 'GPRC_USA']]
print(tail.to_string())
