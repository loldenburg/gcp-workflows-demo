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

    _payload = {'script': 'example_script',
                'workflow_callback_url': "https://www.google.com/your-workflow-callback-url"}
    # _payload = {'add_fin_file': False, 'callback_timeout': 550, 'encoding': 'utf-8', 'ftp_timeout': None,
    #            'gcs_bucket': 'workflow-demo-01-15-private-disposable-1m', 'gcs_file_name': None,
    #            'gcs_folders': ['__test'], 'keep_file_on_ftp': True, 'script': 'ftp_to_gcs', 'source_file_name': None,
    #            'source_file_name_re': '^fragestellung', 'source_folder': '/gcp-workflows/',
    #            'source_ftp': 'my_test_ftp',
    #            'workflow_callback_url': 'https://workflowexecutions.googleapis.com/v1/projects/50418753810/locations/europe-west6/workflows/ftp_to_gcs/executions/e1537ee9-9d70-4f1e-bc3e-4a9d15b02787/callbacks/f133d9d2-911f-4348-9ced-bbedb83f2e40_667c6bf6-c419-416f-9802-e648aae46790'}
    data = dumps(_payload).encode('utf-8')
    _context = Context(eventId="12456646", timestamp="irrelevant", eventType="test", resource="none")

    response = main_handler({"data": base64.b64encode(data)}, _context)
    print(response)
