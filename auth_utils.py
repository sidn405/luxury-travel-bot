import os
import logging
from google.cloud import secretmanager


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def access_secret_version(secret_name, version_id="latest"):
    """
    Access the secret value from Google Secret Manager.
    """
    try:
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "luxury-travel-bot-439000")
        name = f"projects/{project_id}/secrets/{secret_name}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logger.error(f"Failed to access secret {secret_name}: {e}")
        raise
