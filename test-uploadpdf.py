import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import traceback

def authenticate_service_account():
    try:
        credentials = service_account.Credentials.from_service_account_file(
            '/home/info/luxury_travel_bot/luxury-travel-bot-439000.json', scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        credentials.refresh(Request())  # Refresh the access token
        return credentials.token
    except Exception as e:
        print(f"Error during service account authentication: {str(e)}")
        traceback.print_exc()

def upload_to_gcs_json_api(bucket_name, blob_name, file_path):
    try:
        access_token = authenticate_service_account()
        print(f"Access Token: {access_token}")
        upload_url = f"https://www.googleapis.com/upload/storage/v1/b/{bucket_name}/o?uploadType=media&name={blob_name}"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/pdf"}

        with open(file_path, 'rb') as file_data:
            response = requests.post(upload_url, headers=headers, data=file_data)

            # Log the response status and text to debug the issue
            print(f"Upload response status: {response.status_code}, response: {response.text}")

            if response.status_code == 200:
                print(f"File {blob_name} uploaded successfully.")
                return response.json()
            else:
                print(f"Error uploading file: {response.status_code}, {response.text}")
                return None
    except Exception as e:
        print(f"Error uploading to GCS using JSON API: {str(e)}")
        traceback.print_exc()
        return None

# Test the function
if __name__ == "__main__":
    # Ensure you have created a test PDF before running this
    test_file_path = "/tmp/5 day Altanta itinerary.pdf"
    upload_response = upload_to_gcs_json_api("lux-travel-2", "5 day Altanta itinerary.pdf", test_file_path)
    if upload_response:
        print(f"File uploaded. Response: {upload_response}")