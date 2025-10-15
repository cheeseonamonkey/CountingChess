

import csv
import pandas as pd

seed_user = "ffffattyyyy"  # Example seed user
users = fetch_random_users_spider(seed_user, n=1500, m=10, o=3, verbose=True)

df = pd.DataFrame({'username': users})
df.to_csv('ChessUsers.csv', index=False)
print(f"Saved {len(users)} users to ChessUsers.csv")