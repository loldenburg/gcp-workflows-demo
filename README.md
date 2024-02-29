# GCP Workflows Demo

by Lukas Oldenburg, dim28.ch. Part of the Analytics Pioneers demo session in January-April 2024.
Accompanying slides are at https://docs.google.com/presentation/d/11sxK1XKof-yF7wjrN5VFRlk5GBTr9NgFaSdINvjDH1Y (ask for
access if you can't see them).

## Set up GCP Project and enable APIs

**Option 1:**
Run
the [GCP Labs example in this same repo](https://github.com/loldenburg/gcp-workflows-demo/blob/master/gcp-labs-example.md).

**Option 2:**
Create a new Google Cloud Project and switch to it.

Then open Cloud Shell and enable the necessary APIs with the code below:

```bash
gcloud services enable \
  cloudfunctions.googleapis.com \
  run.googleapis.com \
  workflows.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com \
  secretmanager.googleapis.com
```

Then clone this repository as a new project in your local IDE (ideally PyCharm).

## Set up Cloud Cloud Function Infrastructure

### Create a Cloud Storage Bucket

- Name: `{{project-id}}-private-disposable-1m`
  Optional:
- Choose europe-west6 (Zürich) as location (or the location where your cloud function shall run)
- Lifecycle policy (after creation): 1 month

### Create a Secret Manager Secret "my_test_ftp"

- Enable Secret Mgr API
- Create a Secret called `my_test_ftp` in Secret Manager.
- Secret Content: A JSON with the FTP credentials in the following syntax, example:

```json
{
  "address": "myftp.mydomain.com",
  "user": "myusername",
  "passwd": "mypassword",
  "ftp_folder": "/"
}
```

_(Note to Lukas: see git-ignored ftp_login.txt in root of this repo)_

### Do some Code and Rights Changes:

In `cloudbuild.yaml`, change the Service Account to the one you want to use:

```yaml
_SERVICE_ACCOUNT: "1234567890-compute@developer.gserviceaccount.com"  # todo change to the actually intended account
```

- To speed up the demo, we use the default Compute or App Engine service account. We need to give it **"Secret Manager
  Secret Accessor"
  permission** under IAM & Admin.

- In `gcf_src/config/cfg.py`:

```
GCP_PROJECT = environ.get("GCP_PROJECT", "workflow-demo-project") # todo change to actual project ID to enable local runs
```

### Create Cloud Function via Cloud Build

Go to Cloud Build -> Settings -> Enable permissions:

- Cloud Functions Developer
- Cloud Run Admin
- Service Account User

#### Build via Cloud Build:

In your IDE, open a terminal from the root folder of this repository. Then run:

```bash
gcloud config set project !!THEPROJECTID!! # switch to your project
```

Classic command:

```bash
gcloud builds submit --config cloudbuild.yaml --no-gen2 
```

Or: With logs and gcloud beta components installed:

```bash
gcloud beta builds submit --config cloudbuild.yaml --no-gen2 
```

If you run into trouble, update your credentials with:

```bash
gcloud auth login --update-adc
```

### Create Workflow

- name: ftp_to_gcs
- region: europe-west6 (Zürich), everything else default
- Workflow Editor Source Code -> copy from `workflows/ftp-to-gcs.yaml`
- Test the workflow with this payload (this will of course fail because you don't have access to my FTP server):

```json
{
  "import_cfg": {
    "gcs_bucket": "{{YOUR_PROJECT_ID}}-private-disposable-1m",
    "gcs_folders": [
      "__test"
    ],
    "keep_file_on_ftp": true,
    "source_file_name_re": "^frag.*tellung",
    "source_folder": "/gcp-workflows/",
    "source_ftp": "my_test_ftp",
    "callback_timeout": 10
  }
}
```

### Add Cloud Scheduler Job to trigger Workflow regularly

- Edit the workflow
- Add a trigger => Cloud Scheduler
- Give a name and the last payload we used
- Go to Cloud Scheduler and test it via "Force Run"
