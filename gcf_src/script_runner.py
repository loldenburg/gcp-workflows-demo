import json

from gcf_src.config import cfg
from gcf_src.workflows.helpers import workflow_callback_after_run


def run(event_payload):
    """Runs the script with the supplied `event_payload` from pubsub."""

    print("in script_runner: checking event payload for JSON or string")
    script_result = None
    try:

        event_payload = json.loads(event_payload)

        print(f'Script Runner: Going to process this payload: {event_payload}')

        script = event_payload.get('script')

        cfg.SCRIPT = script
        if event_payload.get("workflow_callback_url") is not None:
            cfg.WORKFLOW_CALLBACK_URL = event_payload['workflow_callback_url']
            print(f"Workflow Callback URL in payload, will send callback request there after this run: "
                  f"{cfg.WORKFLOW_CALLBACK_URL}")

        # placeholders, will be overwritten if supported script is found:
        script_result = f"Unsupported payload sent to script_runner: {event_payload}"

        def run_script(**kwargs):
            _ = kwargs  # otherwise IDE code check complains about an unused variable
            raise NotImplementedError(script_result)

        # check payload for script name and import the corresponding script
        if script == "ftp_to_gcs":
            from gcf_src.storage.ftp_to_gcs import run_script
        elif script == "example_script":
            from gcf_src.example_script.example_script import run_script

        script_result = run_script(payload=event_payload)
        print(f"Finished Run with result: {script_result}.")

        workflow_callback_after_run(workflow_callback_payload=script_result)
        cfg.reset_cfg_vars()
        return script_result

    except Exception as e:
        print(f"Error in script_runner: {e}")
        try:
            workflow_callback_after_run(workflow_callback_payload=script_result)
        except Exception as exc:
            # if even this fails... we are in trouble
            cfg.reset_cfg_vars()  # reset cfg vars so they do not persist into the next run
            # raise the error all the way so that we can see it in the logs
            raise Exception(f"Error firing workflow callback URL: {exc} Script Result was: {script_result}.")
        cfg.reset_cfg_vars()  # reset cfg vars so they do not persist into the next run
        return e
