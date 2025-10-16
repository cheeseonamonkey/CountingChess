import csv
import Fetchers

seed_user = "ffffattyyyy"  # Example seed user
users = Fetchers.fetch_random_users_spider(seed_user, n=6999, m=560, o=360, verbose=True)

# Remove duplicates
unique_users = list(set(users))

with open('ChessUsers.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['username'])  # Optional header
    for user in unique_users:
        writer.writerow([user])

print(f"Saved {len(unique_users)} unique users to ChessUsers.csv")