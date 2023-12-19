import os

def ask_for_unique_ID() -> int:
    while True:
        user_input = input("Enter the unique ID of this peer: ")
        if user_input.isdigit():
            return int(user_input)
        else:
            print("Invalid input. Please enter a valid integer.")

def ask_for_folder_path_to_synchronise() -> str:
    user_input = input("Enter the full path of a folder to synchronise: ")
    if os.path.exists(user_input):
        return str(user_input)
    elif os.access(os.path.dirname(user_input), os.W_OK):
        choice = input("Folder does not exist yet. Do you want to create it [y,n] : ")
        if choice == "y" or choice == "Y":
            os.mkdir(user_input)
            return str(user_input)
        elif choice == "n" or choice == "N":
            return None
    else:
        print("Invalid input. Please enter a valid Path.")
