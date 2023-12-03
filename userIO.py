
def ask_for_unique_ID() -> int:
    while True:
        user_input = input("Enter the unique ID of this peer: ")
        if user_input.isdigit():
            return int(user_input)
        else:
            print("Invalid input. Please enter a valid integer.")
