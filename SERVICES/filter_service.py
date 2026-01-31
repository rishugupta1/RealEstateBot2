def filter_projects(df, city, bhk, budget):
    data = df.copy()

    if city:
        data = data[data["city"] == city]
    if bhk:
        data = data[data["bhk"].str.contains(bhk, na=False)]
    if budget:
        data = data[data["price_numeric"] <= budget]

    return data.head(5)
