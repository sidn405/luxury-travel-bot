import requests
from google.auth import default
from google.auth.transport.requests import Request

# Define the authenticate_service_account and generate_download_json_api functions here
def authenticate_service_account():
    try:
        credentials, project = default()
        credentials.refresh(Request())
        return credentials.token
    except Exception as e:
        print(f"Error using default service account: {str(e)}")
        return None

def generate_download_json_api(bucket_name, blob_name, destination_file_path):
    try:
        access_token = authenticate_service_account()
        if not access_token:
            print("Failed to authenticate service account.")
            return None

        download_url = f"https://storage.googleapis.com/storage/v1/b/{bucket_name}/o/{blob_name}?alt=media"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(download_url, headers=headers)
        if response.status_code == 200:
            with open(destination_file_path, 'wb') as file:
                file.write(response.content)
            print(f"File successfully downloaded to: {destination_file_path}")
            return download_url
        else:
            print(f"Error downloading file: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error during file download: {str(e)}")
        return None

# Your code to test download
bucket_name = "lux-travel-2"
blob_name = "5 day Altanta getaway.pdf"

# Call the function to generate the download URL and save the file
download_url = generate_download_json_api(bucket_name, blob_name, "/tmp/5 day Altanta getaway.pdf")
if download_url:
    print(f"Download URL: {download_url}")
else:
    print("Failed to generate download URL.")