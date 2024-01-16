from json import loads
from os import environ

from google.cloud import secretmanager

WORKFLOW_CALLBACK_URL = 'undefined'
SCRIPT = 'undefined'
GCP_PROJECT = environ.get("GCP_PROJECT", "workflow-demo-01-15")  # todo change to actual project ID to enable local runs
GCS_DEFAULT_BUCKET = environ.get("GCS_DEFAULT_BUCKET", f"{GCP_PROJECT}-private-disposable-1m")


def reset_cfg_vars():
    print("Resetting Config Vars so they do not persist into the next run")
    global SCRIPT, WORKFLOW_CALLBACK_URL
    SCRIPT = "undefined"
    WORKFLOW_CALLBACK_URL = "undefined"
    return SCRIPT, WORKFLOW_CALLBACK_URL


def secret_mgr_get_secret(secret_id: str):
    client = secretmanager.SecretManagerServiceClient()
    project_id = GCP_PROJECT
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    decoded = response.payload.data.decode("UTF-8")
    return decoded


# FTP servers. You can add others in the same manner:
def my_test_ftp():
    login_info = loads(secret_mgr_get_secret("my_test_ftp"))
    my_test_ftp.address = login_info["address"]
    my_test_ftp.user = login_info["user"]
    my_test_ftp.passwd = login_info["passwd"]
    my_test_ftp.ftp_folder = login_info["ftp_folder"]
    return my_test_ftp
