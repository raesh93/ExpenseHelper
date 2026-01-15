import pandas as pd

df = pd.read_csv("output/Date_SerNo__Transaction_Details_Reward_Points_Amou.csv")

# Filter out rows with missing dates
df_valid = df[df['Date'].notna() & (df['Date'].str.strip() != '')].copy()

print("=" * 100)
print("✅ FINAL EXTRACTION SUMMARY - ICICI Bank Statement")
print("=" * 100)
print(f"\nTotal transactions extracted: {len(df)}")
print(f"Transactions with valid dates: {len(df_valid)}")
print(f"Transactions with missing dates: {len(df) - len(df_valid)}")

print(f"\n📊 DATE RANGE: {df_valid['Date'].min()} to {df_valid['Date'].max()}")

print(f"\n💰 FINANCIAL SUMMARY:")
amounts = pd.to_numeric(df_valid['Amount (in`)'].str.replace(',', ''), errors='coerce')
print(f"  Total Spent: ₹{amounts.sum():,.2f}")
print(f"  Average Transaction: ₹{amounts.mean():,.2f}")
print(f"  Median: ₹{amounts.median():,.2f}")
print(f"  Highest: ₹{amounts.max():,.2f}")
print(f"  Lowest: ₹{amounts.min():,.2f}")

print(f"\n🎁 REWARD POINTS EARNED: {pd.to_numeric(df_valid['Reward Points'], errors='coerce').sum():.0f}")

print(f"\n📋 FIRST 10 TRANSACTIONS (Chronologically):")
print(df_valid[['Date', 'SerNo.', 'Transaction Details', 'Reward Points', 'Amount (in`)']].head(10).to_string(index=False))

print(f"\n📋 LAST 10 TRANSACTIONS:")
print(df_valid[['Date', 'SerNo.', 'Transaction Details', 'Reward Points', 'Amount (in`)']].tail(10).to_string(index=False))

print("\n" + "=" * 100)
print("OUTPUT FILES CREATED:")
print("=" * 100)
print("  ✓ Date_SerNo__Transaction_Details_Reward_Points_Amou.csv (main transactions)")
print("  ✓ Date_SerNo__Transaction_Details_Reward_Points_Amou.xlsx (Excel format)")
print("  ✓ summary.json (metadata)")
print("  ✓ Plus additional data tables for account summaries and rewards")
print("\n📁 Location: output/ directory")
print("=" * 100)
