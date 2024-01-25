import base64
from typing import Dict

from google.cloud.functions.context import Context

from gcf_src.script_runner import run


def main_handler(event: Dict, context: Context):
    """Background Cloud Function to be triggered by Pub/Sub.
    Args:
         event (dict):  The dictionary with data specific to this type of
         event. The `data` field contains the Pubsub message. The
         `attributes` field will contain custom attributes if there are any.
         context (google.cloud.functions.Context): The Cloud Function event
         metadata. The `event_id` field contains the Pub/Sub message ID. The
         `timestamp` field contains the publish time.
    """
    print(f"Handler triggered by message {context.event_id} published at {context.timestamp}.")

    print(f"The received event is `{event}`.")
    event_payload = None
    if 'data' in event:
        event_payload = base64.b64decode(event['data']).decode('utf-8')
        print(f"The event payload is: `{event_payload}`.")

    return run(event_payload)


if __name__ == "__main__":
    from json import dumps

    _payload = {"script": "example_script",
                "workflow_callback_url": "https://www.google.com/your-workflow-callback-url"}
    # _payload = {'add_fin_file': False, 'callback_timeout': 200, 'encoding': 'utf-8', 'ftp_timeout': None,
    #             'gcs_bucket': 'workflow-demo-01-20-private-disposable-1m', 'gcs_file_name': None,
    #             'gcs_folders': ['__test'], 'keep_file_on_ftp': True, 'source_file_name': None,
    #             'source_file_name_re': '^frag.*tellung', 'source_folder': '/gcp-workflows/',
    #             'source_ftp': 'my_test_ftp',
    #             'workflow_callback_url': 'https://workflowexecutions.googleapis.com/v1/projects/316496625320/locations/europe-west6/workflows/ftp_to_gcs/executions/fc51d350-9e0c-4dd2-a17e-f7a18cd36025/callbacks/50702b45-2c38-42e7-9daa-06acd8fa0316_f56d91fc-0431-44a3-9be0-17d2175459bc'}
    data = dumps(_payload).encode('utf-8')
    _context = Context(eventId="12456646", timestamp="irrelevant", eventType="test", resource="none")

    response = main_handler({"data": base64.b64encode(data)}, _context)
    print(response)
