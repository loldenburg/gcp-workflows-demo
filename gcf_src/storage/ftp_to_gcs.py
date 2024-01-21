from datetime import datetime, timezone, timedelta
from io import StringIO

from gcf_src.config import cfg
from gcf_src.storage import ftp
from gcf_src.storage import gcs


def return_result(result: str = "done", result_detail: object = None, workflow_instructions: dict = None) -> dict:
    """
    Returns the script result and workflow instructions. The workflow instructions are used to tell the workflow what to do next.
    By default, the script returns "done" and no further instructions. => Workflow will do whatever is its default behaviour
    This allows for implicit handling of what to do next inside the Cloud Function instead of managing all kinds of
    results and behaviors in the workflow script itself, because the workflow just needs to do one of three: continue, retry, or exit
    @param result: the script result. Defaults to "done" (success)
    @param result_detail: optional details about the result
    @param workflow_instructions: overrides or sets default instructions for workflow
    """
    workflow_instructions_to_send = {
        "exit": False,  # takes precedence: If True, no more retries and workflow does NOT continue with next step
        "retry": False  # if True, workflow will retry up to its max_attempts
    }
    if isinstance(workflow_instructions, dict):
        # update the instructions with whatever may have come from the script result
        workflow_instructions_to_send.update(workflow_instructions)
    # default: success, no further instructions
    return {"result": result, "result_detail": result_detail,
            "workflow_instructions": workflow_instructions_to_send}


def run_script(**kwargs):
    """Imports a file from FTP to GCS.
    kwargs.payload contains:
    - source_ftp: FTP to import from (eg. "aa_main_prod_export_ftp") - MANDATORY
    - source_folder: FTP folder to import from (eg. "outgoing") - OPTIONAL, defaults to FTP's default folder
    - encoding: encoding of the file to import (eg. "utf-8") - OPTIONAL, defaults to "utf-8"
    - ftp_timeout: timeout for FTP connection (eg. 10) - OPTIONAL, defaults to None (default FTP lib timeout setting will be used)
    - gcs_bucket: GCS bucket to import to - OPTIONAL, defaults to cfg.GCS_DEFAULT_BUCKET
    - gcs_folders: list of GCS folders to import to (eg. ["product-classifications"]) - MANDATORY
    - gcs_file_name: GCS file name to import to (eg. "prods_2021-09-09-10-00-00.txt") - OPTIONAL, defaults to source file name
    - workflow_callback_url: URL to call when the workflow is done - OPTIONAL
    - keep_file_on_ftp: if False, will delete the file from FTP after it has been imported to GCS - OPTIONAL, defaults to False
    - add_fin_file: if True, will add a .fin file to the FTP folder after the file has been imported to GCS (for Adobe Analytics imports) - OPTIONAL, defaults to False
    - one of:
        - source_file_name_re: regex, will do the import for multiple files
        - source_file_name: single file name, will do the import for a single file
    """
    print(f"Starting script to import file(s) from FTP to GCS with locals: {locals()}")

    test = False
    payload = kwargs.get("payload", {})
    workflow_callback_url = payload.get("workflow_callback_url")
    source_ftp = payload.get("source_ftp")
    if source_ftp is None:
        raise Exception("source_ftp must be provided in payload.")
    source_ftp_cfg = getattr(cfg, source_ftp)()  # eg. "aa_main_prod_export_ftp"
    source_file_name_re = payload.get("source_file_name_re", None)  # regex, will do the import for multiple files
    source_file_name = payload.get("source_file_name", None)  # single file name, will do the import for a single file
    if source_file_name_re is None and source_file_name is None:
        raise Exception("Either source_file_name_re or source_file_name must be provided in payload.")
    source_folder = payload.get("source_folder") or source_ftp_cfg.folder
    encoding = payload.get("encoding") or "utf-8"
    ftp_timeout = payload.get("ftp_timeout")
    keep_file_on_ftp = payload.get("keep_file_on_ftp") or False
    add_fin_file = payload.get("add_fin_file") or False

    source_host = source_ftp_cfg.address
    source_user = source_ftp_cfg.user
    print(f"source_host: {source_host}, source_file_name_re: {source_file_name_re}, "
          f"source_file_name: {source_file_name}, source_folder: {source_folder}, encoding: {encoding}, "
          f"timeout: {ftp_timeout}, source_user: {source_user}")
    source_pwd = source_ftp_cfg.passwd

    gcs_bucket = payload.get("gcs_bucket") or cfg.GCS_DEFAULT_BUCKET
    gcs_folders = payload.get("gcs_folders")
    if gcs_folders is None:
        raise Exception("gcs_folders must be provided in payload.")

    print(f"gcs_bucket: {gcs_bucket}, gcs_folder: {gcs_folders}")
    if source_file_name is not None:
        files_on_source_ftp = [source_file_name]
    else:  # = a regular Expression to search for multiple files was provided
        files_on_source_ftp = ftp.list_files_on_ftp(file_name_re=source_file_name_re, ftp_address=source_host,
                                                    ftp_user=source_user, ftp_passwd=source_pwd,
                                                    ftp_folder=source_folder)
        if len(files_on_source_ftp) == 0:
            msg = f"no_matches_on_ftp"
            print(msg)
            return return_result(result=msg, workflow_instructions={"exit": True})
        print(f"Found the following files on FTP: {files_on_source_ftp}")

        if len(files_on_source_ftp) > 1:
            # process the oldest file first.
            files_on_source_ftp = sorted(files_on_source_ftp, reverse=True)

    gcs_locations = []  # will contain a list of all exported files' GCS locations
    for ftp_file_name in files_on_source_ftp:
        print(f"Checking if file {ftp_file_name} has been completely uploaded already to FTP")
        # we cannot be 100% sure, but we can check if the file was last modified at least 10 minutes ago (an upload should never take that long)
        modification_date = ftp.get_file_modification_date(file_name=ftp_file_name, ftp_address=source_host,
                                                           ftp_user=source_user, ftp_passwd=source_pwd,
                                                           ftp_folder=source_folder)
        now = datetime.now(timezone.utc)
        if modification_date > datetime.now() - timedelta(seconds=30):
            print(
                f"File {ftp_file_name}'s modification date is {modification_date}, so it may not have been completely uploaded yet to FTP. Stopping.")
            # we want the workflow to retry later. Since we are sorting the files in a way that we are processing the newest files first,
            # it will not happen that there are any other (newer) unprocessed files on the FTP
            return return_result(result="file_not_ready_yet", workflow_instructions={"retry": True})
        print(
            f"File {ftp_file_name}'s modification date is {modification_date}, so it has been completely uploaded already to FTP. Continuing.")

        print("Importing file from FTP to GCS: " + ftp_file_name)
        try:

            source_file = ftp.download_from_ftp(file_name=ftp_file_name, ftp_address=source_host,
                                                ftp_user=source_user, ftp_passwd=source_pwd,
                                                ftp_folder=source_folder, timeout=ftp_timeout)
        except Exception as e:
            msg = f"Error while downloading file {ftp_file_name} from FTP: {e}"
            # this happens quite often, so we don't want to raise the Exception to the top (would cause false alerts)
            print(msg)
            return return_result(result="ftp_error", result_detail=msg, workflow_instructions={"retry": True})

        print(
            f"Downloaded from FTP. Now transferring {ftp_file_name} to GCS bucket {gcs_bucket} and folder {gcs_folders}")

        gcs_file_name = payload.get("gcs_file_name") or ftp_file_name

        for gcs_folder in gcs_folders:
            if gcs_folder[-1] != "/":
                # append "/" to folder name if it is not there yet to make concatenation of folder to file name easier
                gcs_folder += "/"
            gcs_location = gcs_folder + gcs_file_name
            gcs.upload_file(dest_file_name=gcs_location, bucket_name=gcs_bucket, data=source_file,
                            file_encoding=encoding)
            gcs_locations.append(gcs_location)
            print(
                f"Transferred file {ftp_file_name} to GCS bucket {gcs_bucket} and location {gcs_location}")

        if keep_file_on_ftp is False:
            print(f"Deleting file {ftp_file_name} from FTP")
            ftp.delete_file(ftp_folder=source_folder, file_name=ftp_file_name, ftp_address=source_host,
                            ftp_user=source_user,
                            ftp_passwd=source_pwd)
            print(f"Deleted file {ftp_file_name} from FTP")

        if add_fin_file is True:
            print("Adding .fin file to FTP so Adobe Analytics can start importing it.")
            finfile_buffer = StringIO()
            finfile_name = ftp_file_name.split(".")[0] + ".fin"
            ftp.upload_to_ftp(finfile_buffer,
                              file_name=finfile_name,
                              ftp_address=source_host,
                              ftp_user=source_user,
                              ftp_passwd=source_pwd,
                              ftp_folder=source_folder, file_encoding=encoding)
            print(f"Uploaded fin file {finfile_name} to FTP")

    return {"result": "done", "workflow_instructions": {"gcs_locations": gcs_locations}}


if __name__ == '__main__':
    run_script(payload={'add_fin_file': False, 'callback_timeout': 540, 'encoding': 'utf-8', 'ftp_timeout': None,
                        'gcs_bucket': 'workflow-demo-01-20-private-disposable-1m', 'gcs_file_name': None,
                        'gcs_folders': ['__test'], 'keep_file_on_ftp': True, 'script': 'ftp_to_gcs',
                        'source_file_name': None, 'source_file_name_re': '^frag.*tellung',
                        'source_folder': '/gcp-workflows/', 'source_ftp': 'my_test_ftp',
                        'workflow_callback_url': 'https://workflowexecutions.googleapis.com/v1/projects/316496625320/locations/europe-west6/workflows/ftp_to_gcs/executions/e397a3fe-457c-47a5-977e-570d8d9f8d2d/callbacks/f82ec947-e44a-4f6b-b0ca-8eb42b96033c_679db4cd-f48c-4339-b0a9-90d07a5bf9d8'})
