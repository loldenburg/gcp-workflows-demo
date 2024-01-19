import google.auth
import google.auth.transport.requests
import google.oauth2.credentials
import requests

from gcf_src.config import cfg


def generate_gcp_access_token() -> str:
    """
    Authenticates a request to a google workflows callback from a cloud function. See
    https://stackoverflow.com/questions/76234915/trouble-authenticating-a-request-to-a-google-workflows-callback-from-a-cloud-fun
        :return: access token
    """
    credentials, project_id = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    request = google.auth.transport.requests.Request()
    credentials.refresh(request)
    access_token = credentials.token
    return access_token


def trigger_workflow_callback(request_type: str = "POST", workflow_callback_url: str = None, headers: dict = None,
                              data: dict = None, raise_error: bool = True) -> requests.Response:
    """
    Triggers a workflow by sending a request (GET or POST) to the provided callback URL.

    Args:
        request_type (str): The type of the request. Must be either 'GET' or 'POST'.
        workflow_callback_url (str, optional): The URL to send the request to in order to trigger the workflow.
        headers (dict, optional): A dictionary of headers to include in the request. Defaults to None.
        data (dict, optional): A dictionary of data to include in the request if a POST request is being made. Defaults to None.
        raise_error (bool, optional): A flag that determines whether to raise an Exception if the request is unsuccessful.
            If True, an Exception is raised. If False, a warning is logged. Defaults to True.

    Returns:
        requests.Response: The Response object from the request.

    Raises:
        Exception: If the request is unsuccessful and 'raise_error' is True, an Exception is raised.
    """
    token = generate_gcp_access_token()
    headers = headers or {}
    headers.update({'Authorization': f'Bearer {token}'})

    if request_type.upper() == 'GET':
        wf_response = requests.get(workflow_callback_url, headers=headers)
    elif request_type.upper() == 'POST':
        wf_response = requests.post(workflow_callback_url, headers=headers,
                                    json=data)  # json parameter is necessary, otherwise Workflow will not be able to read it and treat it as JSON
    else:
        raise ValueError("request_type must be either 'GET' or 'POST'")

    if wf_response.status_code == 200:
        print(f"Workflow callback URL {workflow_callback_url} successfully triggered "
              f"\nvia {request_type}"
              f"\nwith headers: {headers}"
              f"\nbody data (if POST): {data}."
              f"\nResponse: {wf_response}")
    else:
        msg = f"Workflow callback URL could not be triggered. Response: {wf_response}"
        if raise_error:
            print(msg)
            raise Exception(msg)
        else:
            print(msg)
    return wf_response


def workflow_callback_after_run(workflow_callback_payload: dict = None):
    if cfg.WORKFLOW_CALLBACK_URL != "undefined":
        # enrich payload with script and script_run_id
        workflow_callback_payload.update({"script": cfg.SCRIPT})
        print(f"Triggering Workflow Callback URL with Payload: {workflow_callback_payload}")
        trigger_workflow_callback(workflow_callback_url=cfg.WORKFLOW_CALLBACK_URL, request_type="POST",
                                  data=workflow_callback_payload)


if __name__ == '__main__':
    # test callback URL here
    url = "https://workflowexecutions.googleapis.com/v1/projects/50418753810/locations/europe-west6/workflows/ftp_to_gcs/executions/5777f9ae-821a-4362-88a7-d2e06be319a4/callbacks/ff90ce49-373f-4c05-8bc2-e3983654c3ad_08badb84-0f0a-4fb6-897f-ac621e7a9c6a"
    response = trigger_workflow_callback(workflow_callback_url=url, request_type="POST",
                                         data={"result": "error", "result_detail": "some message"})
    print("done")
