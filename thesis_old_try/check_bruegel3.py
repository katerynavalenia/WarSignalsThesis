import pandas as pd
import warnings
warnings.filterwarnings("ignore")

# Try reading with header=0 first
df = pd.read_excel(
    r"C:\Users\A00010311\Downloads\Master Thesis\Europe-Central-Asia_aggregated_data_up_to_week_of-2026-06-06.xlsx",
    header=0
)
print("Shape:", df.shape)
print("Columns:", df.columns.tolist()[:20])
print("All columns count:", len(df.columns))
print("\nFirst 5 rows (first 8 cols):")
print(df.iloc[:5, :8].to_string())
print("\nDate column check - first col unique sample:")
print(df.iloc[:10, 0].tolist())
print("\nLast rows:")
print(df.iloc[-3:, :5].to_string())
