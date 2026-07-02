import os
from instagrapi import Client

def challenge_code_handler(username, choice):
    if choice == 1:
        print("Instagram sent a code to your SMS/Phone.")
        return input("Enter the 6-digit code: ")
    elif choice == 2:
        print("Instagram sent a code to your Email.")
        return input("Enter the 6-digit code: ")
    return input("Enter the verification code: ")

def generate_session():
    USERNAME = "vinay_3ditz"
    PASSWORD = "instaupload"
    SESSION_FILE = "session.json"
    
    print(f"Logging in to Instagram as {USERNAME}...")
    cl = Client()
    cl.challenge_code_handler = challenge_code_handler
    
    try:
        cl.login(USERNAME, PASSWORD)
        print("Login successful!")
        
        # Save session to file
        cl.dump_settings(SESSION_FILE)
        print(f"Session saved successfully to {SESSION_FILE}!")
        print("\nYou never have to run this script again. The cloud server will use this file to log in.")
        
    except Exception as e:
        print(f"Failed to log in: {e}")
        print("\nIf it asks for verification, open Instagram on your phone and click 'This was me', then run this again.")

if __name__ == "__main__":
    generate_session()
