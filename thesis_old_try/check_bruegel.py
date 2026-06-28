import pandas as pd
import warnings
warnings.filterwarnings("ignore")

df = pd.read_excel("Europe-Central-Asia_aggregated_data_up_to_week_of-2026-06-06.xlsx")
print("Shape:", df.shape)
print("All columns:", df.columns.tolist())
print("\nFirst 5 rows (first 10 cols):")
print(df.iloc[:5, :10].to_string())
print("\ndtypes:")
print(df.dtypes.to_string())
