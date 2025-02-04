import requests
import os
import json
import sys
import pyotp
from debugpy.adapter import access_token

TOKEN_FILEPATH = "/tmp/.bd_tokens"

ACCESS_TOKEN_KEY = "TP_ACCESS_TOKEN"
REFRESH_TOKEN_KEY = "TP_REFRESH_TOKEN"

# bigdata one-time pw secret from 1PW
otp_secret = os.environ.get("bigdata_otp_secret")
if otp_secret is None:
    raise Exception("No OTP Secret found in env vars.")
totp = pyotp.TOTP(otp_secret.replace(" ", ""))


class TPAPITokenExpiredError(Exception):
    pass


def load_persisted_token_to_env():
    """
    Load tokens stored in file for persistence into env variables
    """
    tokens_loaded = False
    if os.path.exists(TOKEN_FILEPATH):
        access_token, refresh_token = open(TOKEN_FILEPATH).readlines()[0].split(",")
        os.environ[ACCESS_TOKEN_KEY] = access_token
        os.environ[REFRESH_TOKEN_KEY] = refresh_token

        tokens_loaded = True

    return tokens_loaded


def generate_new_token(username, password):
    """
    Auth process new in 2025 to hit the Tidepool api for big data donors.

    This function should be run sparingly, only when the token session has expired.

    This generates a new access token and refresh token and then
     1) writes them to a file for persistence across python runs
     2) stores them in environment variables for immediate use
    """

    api_call = "https://auth.tidepool.org/realms/tidepool/protocol/openid-connect/token"
    client_secret = os.environ.get("cid")
    if client_secret is None:
        raise Exception("No client secret for token generation found in env vars.")

    open_auth_api_response = requests.post(api_call, data={
            "client_id": "tidepool-data-science",
            "client_secret": client_secret,
            "username": username,
            "password": password,
            "scope": "openid",
            "otp": totp.now(),
            "grant_type": "password"},
           headers={'Content-Type': 'application/x-www-form-urlencoded'}
    )

    if (open_auth_api_response.ok):
        openid_auth_response_content = json.loads(open_auth_api_response.content)
        access_token = openid_auth_response_content["access_token"]
        refresh_token = openid_auth_response_content["refresh_token"]

        with open(TOKEN_FILEPATH, "w") as f:
            f.write(f"{access_token},{refresh_token}")

        tokens_loaded = load_persisted_token_to_env()
        assert tokens_loaded

        print("Token generated, saved to file, and loaded to env.")

    else:
        sys.exit(f"Error getting API token with {username}. Code: {str(open_auth_api_response.status_code)}. Text: {open_auth_api_response.text}")


def get_auth_user_id(access_token):
    """
    Get the user id for the authorized user associated with the access token

    Also used for testing token expiration
    """
    user_api_response = requests.get("https://api.tidepool.org/auth/user",
                                     headers={"x-tidepool-session-token": access_token,
                                              "Content-Type": "application/json"})

    if user_api_response.status_code == 401:  # forbidden means token expired
        raise TPAPITokenExpiredError

    user_response_content = json.loads(user_api_response.content)
    user_id = user_response_content["userid"]

    return user_id


def retrieve_existing_token(username, password):
    """
    Auth for programmatic access to TP Big Data Project donor data.

    Get existing token from env variables or persisted file

    If no token found, generate and save new token
    If token found but expired, generate and save new token
    """

    tokens_loaded = load_persisted_token_to_env()

    # Case: token not persisted, new run needs new token
    if not tokens_loaded:
        do_generate_new_token = input("No API access token in env variables. (Y) Get a new one, (n) exit.")
        if do_generate_new_token.lower() == "y":
            generate_new_token(username, password)
    else:
        print("Persisted token found.")

    access_token = os.environ.get(ACCESS_TOKEN_KEY) # get new or old token

    # Case: check token expired, if so generate new
    try:
        get_auth_user_id(access_token)
        print("Token valid.")
    except TPAPITokenExpiredError:
        print("Token expired. Generating new one...")
        generate_new_token(username, password)
        access_token = os.environ.get(ACCESS_TOKEN_KEY)  # get renewed token

    return access_token


def logout(username, password):
    """
    Logout of account
    """
    logout_api_call = "https://api.tidepool.org/auth/logout"
    api_response = requests.post(logout_api_call, auth=(username, password))

    if (api_response.ok):
        print("Successfully logged out of", username)
    else:
        sys.exit(f"Error with logging out for {username}: {str(api_response.status_code)}" )