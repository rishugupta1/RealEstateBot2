import pandas as pd
import re

SHEET_URL = "https://docs.google.com/spreadsheets/d/1htI7HBmHTMHz9jxQiP2kEoh3v3YydzNt_Xsov84E7Ig/export?format=csv"

def load_projects():
    df = pd.read_csv(SHEET_URL)

    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df["project_name"] = df["project_name"].astype(str).str.lower()
    df["city"] = df["city"].astype(str).str.lower()
    df["bhk"] = df["bhk"].astype(str).str.lower()

    def clean_price(val):
        try:
            val = str(val).lower().replace("₹", "").replace(",", "")
            if "cr" in val:
                return float(re.findall(r"\d+\.?\d*", val)[0]) * 10000000
            if "l" in val:
                return float(re.findall(r"\d+\.?\d*", val)[0]) * 100000
        except:
            return None

    df["price_numeric"] = df["price"].apply(clean_price)
    return df
