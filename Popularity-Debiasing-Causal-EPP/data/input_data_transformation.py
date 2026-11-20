import pandas as pd

# Load raw Ciao dataset
df = pd.read_csv(
    r"C:\Users\paruk\Downloads\archive (3)\rating.txt",
    sep="::::",
    engine="python",
    header=None,
    dtype=str
)

# Extract required columns
ratings = df[[0, 3, 5]].copy()
ratings.columns = ["user", "rating", "date"]

# Extract item name and category to create unique item identifiers
item_data = df[[1, 2]].copy()
item_data.columns = ["item_name", "category"]

ratings["item_key"] = (
    item_data["category"].str.strip() + "||" +
    item_data["item_name"].str.strip()
)

# Normalize ratings: 30 -> 3, 40 -> 4, 50 -> 5
ratings["rating"] = pd.to_numeric(
    ratings["rating"], errors="coerce"
).map({30: 3, 40: 4, 50: 5})

# Parse dates: DD.MM.YYYY -> Unix timestamp (seconds)
dates = pd.to_datetime(
    ratings["date"],
    format="%d.%m.%Y",
    errors="coerce",
    utc=True
)

ratings["timestamp"] = dates.astype("int64") // 10**9

# Remove invalid records
ratings = ratings.dropna(subset=["user", "item_key", "rating"])
ratings = ratings[dates.notna()]

# Convert user and item IDs to consecutive integers
ratings["user"] = pd.factorize(ratings["user"])[0]
ratings["item"] = pd.factorize(ratings["item_key"])[0]

# Final four columns only
ratings = ratings[["user", "item", "rating", "timestamp"]]

# Correct data types
ratings = ratings.astype("int64")

# Chronological ordering
ratings = ratings.sort_values("timestamp")

# Save without headers or index
ratings.to_csv("ratings.csv", index=False, header=False)

print("Created ratings.csv:", ratings.shape)