import os
from instagrapi import Client

def generate_session():
    USERNAME = "vinay_3ditz"
    PASSWORD = "S!v3XypBZ8D8T*v"
    SESSION_FILE = "session.json"
    
    print(f"Logging in to Instagram as {USERNAME}...")
    cl = Client()
    
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
