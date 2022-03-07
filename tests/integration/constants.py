import os

#: Location of the Firebase Realtime Database Emulator
TESTING_DATABASE_URL = os.environ.get("TESTING_DATABASE_URL", "http://127.0.0.1:9051")

#: Project ID to use for testing
TESTING_PROJECT_ID = os.environ.get("TESTING_PROJECT_ID", "demo-firebasil-test")

EXAMPLE_USER_PASSWORD = "password1"
