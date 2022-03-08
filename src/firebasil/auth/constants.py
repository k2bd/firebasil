import os

#: Location of the Firebase Auth Emulator, if applicable
FIREBASE_AUTH_EMULATOR_HOST = os.environ.get("FIREBASE_AUTH_EMULATOR_HOST")
if FIREBASE_AUTH_EMULATOR_HOST and FIREBASE_AUTH_EMULATOR_HOST.startswith("localhost"):
    FIREBASE_AUTH_EMULATOR_HOST = "http://" + FIREBASE_AUTH_EMULATOR_HOST
