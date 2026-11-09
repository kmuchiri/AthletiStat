import pandas as pd

df=pd.read_csv('data/datasets/seasons/combined_track_field_performances_2001_2026.csv')
df["mark"] = df["mark"].astype(str)
df["wind"] = df["wind"].astype(str)
df.to_parquet('data/datasets/seasons/combined_track_field_performances_2001_2026.parquet',engine="pyarrow", index=False)
