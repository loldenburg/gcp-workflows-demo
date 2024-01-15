# GCP Workflows Demo

by Lukas Oldenburg, dim28.ch. Part of the Analytics Pioneers demo session in January-February 2024.
Accompanying slides are at https://docs.google.com/presentation/d/11sxK1XKof-yF7wjrN5VFRlk5GBTr9NgFaSdINvjDH1Y (ask for
access if you can't see them).

## Run the GCP Labs example

See gcp-s-example.md

In the project we just created for the GCP Labs example, we will do the following steps:

## Set up Cloud Cloud Function Infrastructure

### Create a Cloud Storage Bucket

Name: "private-disposable-1m"
Choose europe-west6 (Zürich) as location
Lifecycle policy (after creation): 1 month

### Create a Secret Manager Secret "ftp_passwd"

Enable Secret Mgr API and store "ftp_passwd" in Secret Manager.
Secret Content: see ftp_login.txt in root of this repo.

### Do some Code Changes:

In cfg:

```
GCP_PROJECT = environ.get("GCP_PROJECT", "workflow-demo-project") # todo change to actual project ID
```

In cloudbuild.yaml:

```
  _SERVICE_ACCOUNT: "xxxxx-compute@developer.gserviceaccount.com"  # todo change to the actually intended account 
```

### Create Cloud Function via Cloud Build Trigger

Create a Cloud Function via Cloud Build (cloudbuild.yaml) and deploy it to Cloud Run.
Cloud Build -> Settings -> Enable permissions:

- Cloud Functions Developer
- Cloud Run Admin
- Service Account User

#### Build via Cloud Build:

```bash
gcloud set project !!THEPROJECTID!!
gcloud builds submit --config cloudbuild.yaml
# or: With logs and gcloud beta components installed:
gcloud beta builds submit --config cloudbuild.yaml
```

### Create Workflow

- name: ftp_to_gcs
- region: europe-west6 (Zürich), everything else default
- Workflow Editor Source Code -> copy from `workflows/workflow.yaml`
- To speed up the demo, we use the default service account. We need to give it **"Secret Manager Secret Accessor"
  permission** under IAM & Admin.
- Test the workflow with this payload:

```json
{
  "import_cfg": {
    "gcs_folders": [
      "__test"
    ],
    "keep_file_on_ftp": true,
    "source_file_name_re": "fragestellung",
    "source_folder": "/gcp-workflows/",
    "source_ftp": "my_test_ftp"
  }
}
```

### Add Cloud Scheduler Job to trigger Workflow regularly

- Edit the workflow
- Add a trigger => Cloud Scheduler
- Give a name and the last payload we used
- Go to Cloud Scheduler and test it via "Force Run"