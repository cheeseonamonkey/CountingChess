import csv
import Fetchers

seed_user = "ffffattyyyy"  # Example seed user
users = Fetchers.spider_users(seed_user,
                                           n=6999,
                                           m=560,
                                           o=360,
                                           verbose=True)

# Remove duplicates
unique_users = list(set(users))

with open('ChessUsers.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['username'])  # Optional header
    for user in unique_users:
        writer.writerow([user])

print(f"Saved {len(unique_users)} unique users to ChessUsers.csv\n")

user_list = []
with open('ChessUsers.csv', 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        user_list.append(row['username'])
Fetchers.fetch_all_users_games(user_list, 50, True)
