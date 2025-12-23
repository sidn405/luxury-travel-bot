from google.cloud import storage

def list_buckets():
    try:
        storage_client = storage.Client(project="luxury-travel-bot-439000")
        buckets = list(storage_client.list_buckets())
        print("Buckets in project:")
        for bucket in buckets:
            print(bucket.name)
    except Exception as e:
        print(f"Error listing buckets: {e}")

if __name__ == "__main__":
    list_buckets()

