from google.cloud import storage

def test_upload():
    bucket_name = "lux-travel-2"
    blob_name = "test-upload.pdf"
    file_path = "/tmp/test.pdf"

    # Create a sample file in the /tmp directory
    try:
        with open(file_path, "w") as test_file:
            test_file.write("This is a test file for GCS upload.")
        print(f"Test file created at {file_path}")
    except Exception as e:
        print(f"Error creating test file: {e}")
        return

    # Upload the file to GCS
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(file_path)
        blob.make_public()  # Make the file public
        print(f"File uploaded successfully. Public URL: {blob.public_url}")
    except Exception as e:
        print(f"Error uploading file: {e}")

if __name__ == "__main__":
    test_upload()

