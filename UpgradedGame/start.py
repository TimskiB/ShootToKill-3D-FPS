import os

os.system(f"pip install -r requirements.txt")
os.chdir(f"{os.getcwd()}/Client")
os.system("python app.py")

