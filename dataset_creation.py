import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta

# -----------------------------
# CONFIGURATION
# -----------------------------

NUM_ROWS = 50000   # Increase rows here
START_DATE = datetime(2024, 1, 1)

assets = ["AAPL","MSFT","GOOG","AMZN","TSLA","NVDA","META","JPM","BAC","GS","NFLX","AMD"]

traders = [
    "Alice Chen","Rahul Sharma","Michael Scott",
    "Sophia Lee","Daniel Kim","Priya Mehta",
    "Carlos Diaz","Emily Johnson"
]

desks = [
    "Equities","Derivatives","Macro","Quant","Fixed Income"
]

venues = [
    "NYSE","NASDAQ","BATS","DARK_POOL","CBOE"
]

sides = ["BUY","SELL"]

market_events = [
    "NONE",
    "EARNINGS_RELEASE",
    "FED_POLICY",
    "MACRO_NEWS",
    "HIGH_VOLATILITY",
    "MERGER_NEWS"
]

order_types = [
    "MARKET",
    "LIMIT",
    "STOP",
    "ALGO"
]

# Base prices
base_prices = {
    "AAPL":180,"MSFT":330,"GOOG":140,"AMZN":120,"TSLA":220,
    "NVDA":700,"META":350,"JPM":150,"BAC":35,"GS":400,
    "NFLX":450,"AMD":120
}

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------

def random_timestamp():
    minutes = random.randint(0, 60*24*365)
    return START_DATE + timedelta(minutes=minutes)

def generate_price(asset):
    base = base_prices[asset]
    return round(np.random.normal(base, base*0.02),2)

def generate_volatility():
    return round(np.random.uniform(0.01,0.05),4)

def market_impact(size, volatility):
    impact = (size/100000) * volatility * random.uniform(0.8,1.5)
    return round(impact,5)

def liquidity_score():
    return round(np.random.uniform(0.3,1.0),3)

# -----------------------------
# DATA GENERATION
# -----------------------------

rows = []

for trade_id in range(1, NUM_ROWS+1):

    asset = random.choice(assets)
    price = generate_price(asset)
    size = random.randint(100,100000)

    volatility = generate_volatility()

    row = {
        "trade_id": trade_id,
        "timestamp": random_timestamp(),
        "asset": asset,
        "side": random.choice(sides),
        "price": price,
        "size": size,
        "notional_value": round(price*size,2),
        "trader": random.choice(traders),
        "desk": random.choice(desks),
        "venue": random.choice(venues),
        "order_type": random.choice(order_types),
        "volatility": volatility,
        "liquidity_score": liquidity_score(),
        "market_event": random.choice(market_events),
        "market_impact_estimate": market_impact(size,volatility),
        "slippage": round(np.random.normal(0,0.02),4),
        "pnl": round(np.random.normal(0, price*size*0.001),2)
    }

    rows.append(row)

# -----------------------------
# CREATE DATAFRAME
# -----------------------------

df = pd.DataFrame(rows)

# Sort by timestamp
df = df.sort_values("timestamp")

# -----------------------------
# SAVE CSV FILE
# -----------------------------

file_name = "synthetic_trade_data.csv"
df.to_csv(file_name,index=False)

print(f"\nDataset created successfully!")
print(f"Rows generated: {len(df)}")
print(f"File saved as: {file_name}")

print("\nSample Data:")
print(df.head())