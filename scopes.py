from auth_utils import access_secret_version
from google.oauth2 import service_account


def load_credentials_from_secret(secret_name="TravelManager"):
    """
    Load service account credentials from Secret Manager.
    """
    try:
        key_data = access_secret_version(secret_name)
        credentials = service_account.Credentials.from_service_account_info(
            eval(key_data),  # Convert JSON string to Python dictionary
            scopes=["https://www.googleapis.com/auth/devstorage.read_write"],
        )
        return credentials
    except Exception as e:
        print(f"Error loading credentials: {e}")
        raise


# Display scopes and project for debugging
if __name__ == "__main__":
    credentials = load_credentials_from_secret("TravelManager")
    print(f"Scopes: {credentials.scopes}")
    print(f"Project: {credentials.project_id}")
