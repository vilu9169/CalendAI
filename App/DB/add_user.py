from sqlite import CalendarDB

while True:
    name = input("Enter username: ")
    if not name.isalnum():
        print("Username contains illegal characters. Only alphanumeric characters are allowed.")
        continue
    break
while True:
    password = input("Enter password: ")
    if len(password) < 6:
        print("Password must be at least 6 characters long.")
        continue
    break
while True:
    email = input("Enter email: ")
    if "@" not in email or "." not in email.split("@")[-1]:
        print("Invalid email format.")
        continue
    break

db = CalendarDB()
db.add_user(name, password, email)

print(db.get_user(name))
