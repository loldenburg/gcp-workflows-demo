# Guide
Slightly modified and corrected version of https://codelabs.developers.google.com/codelabs/cloud-workflows-intro#6

# Connect 2 Cloud Functions together with a workflow

Create a new GCP project.

## Enable APIs
Open Cloud Shell. Enable all necessary services, e.g. via Cloud Shell:

```bash
gcloud services enable \
  cloudfunctions.googleapis.com \
  run.googleapis.com \
  workflows.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com
```

## Create and deploy first Cloud Function

Create and navigate to a directory for the function code:

```bash
mkdir ~/randomgen
cd ~/randomgen
```

Create a main.py file in the directory with the following contents:

```python
import random, json
from flask import jsonify


def randomgen(request):
    randomNum = random.randint(1, 100)
    output = {"random": randomNum}
    return jsonify(output)
```

When it receives an HTTP request, this function generates a random number between 1 and 100 and returns in JSON format back to the caller.

To create the file, you can use the nano editor:

`nano main.py`

In nano, you paste the text and then save the file by pressing Ctrl + O, hitting Enter, and then exiting with Ctrl + X. 

The function relies on Flask for HTTP processing and we need to add that as a dependency. Dependencies in Python are managed with pip and expressed in a metadata file called requirements.txt.

Create a requirements.txt file in the same directory with the following contents:

```requirements.txt
flask<3.0.0 # functions-framework does not support Flask 3.0.0 yet
```

Deploy the function with an HTTP trigger and with unauthenticated requests allowed with this command:

```bash
gcloud functions deploy randomgen \
    --runtime python312 \
    --trigger-http \
    --allow-unauthenticated
```

Once the function is deployed, you can see the URL of the function under httpsTrigger.url property displayed in the
console (=> Menu: Cloud Functions) or in the shell via

```bash
gcloud functions describe randomgen
```

You can also visit that URL of the function (=run the function) with the following curl command:

```bash
curl $(gcloud functions describe randomgen --format='value(httpsTrigger.url)')
```

The first function is ready for the workflow.

## Deploy second Cloud Function
The second function is a multiplier. It multiplies the received input by 2.

Create and navigate to a directory for the function code:

```bash
mkdir ~/multiply
cd ~/multiply
```

Via `nano` like above, create a main.py file in the directory with the following contents:

```python
import random, json
from flask import jsonify

def multiply(request):
    request_json = request.get_json()
    output = {"multiplied":2*request_json['input']}
    return jsonify(output)
```

When it receives an HTTP request, this function extracts the input from the JSON body, multiplies it by 2 and returns in JSON format back to the caller.

Create the same requirements.txt file in the same directory with the following contents:

```requirements.txt
flask<3.0.0 # functions-framework does not support Flask 3.0.0 yet
```

Deploy the function with an HTTP trigger and with unauthenticated requests allowed with this command:

```bash
gcloud functions deploy multiply \
    --runtime python312 \
    --trigger-http \
    --allow-unauthenticated
```
Once the function is deployed, you can also visit that URL of the function with the following curl command:

```bash
curl $(gcloud functions describe multiply --format='value(httpsTrigger.url)') \
-X POST \
-H "content-type: application/json" \
-d '{"input": 5}'
```
=> should return `{"multiplied":10}`

The second function is ready for the workflow.

## Create a workflow to connect the two Cloud Functions

In the first workflow, connect the two functions together.

Create a workflow.yaml file in the root folder with the following contents.
If `us-central1` is not your default region, replace it with your region.

```yaml
- randomgenFunction:
    call: http.get
    args:
        url: https://us-central1-workflow-demo-12-16.cloudfunctions.net/randomgen
    result: randomgenResult
- log_randomgenResult:
    call: sys.log
    args:
      severity: "INFO"
      text: ${"Received random number " + randomgenResult.body.random}
- multiplyFunction:
    call: http.post
    args:
        url: https://us-central1-workflow-demo-12-16.cloudfunctions.net/multiply
        body:
            input: ${randomgenResult.body.random}
    result: multiplyResult
- returnResult:
    return: ${multiplyResult}
```

Deploy the first workflow:

```bash
gcloud workflows deploy workflow --source=workflow.yaml
```

Execute the first workflow:

```bash
gcloud workflows execute workflow
```

Once the workflow is executed, you can see the result by passing in the execution id given in the previous step:

```bash
gcloud workflows executions describe <your-execution-id> --workflow workflow
```

The output will include result and state:

```txt
result: '{"body":{"multiplied":108},"code":200 ... } 

...
state: SUCCEEDED
```

## Connect an External API
Next, you will connect math.js as an external service in the workflow.

In math.js, you can evaluate mathematical expressions like this:

https://api.mathjs.org/v4/?expr=log(56)


This time, you will use Cloud Console to update our workflow. Search for "Workflows" in Google Cloud Console and navigate to the Workflows page. Click on the workflow you created in the previous step, then Source -> Edit.

Our new workflow source should look like this:

```yaml
- randomgenFunction:
    call: http.get
    args:
        url: https://us-central1-workflow-demo-12-16.cloudfunctions.net/randomgen # instead of us-central1-workflow-demo-12-16, use your {region-projectID}  
    result: randomgenResult
- logRandomgenResult:
    call: sys.log
    args:
      severity: "INFO"
      text: ${"Received random number " + randomgenResult.body.random +" from randomgenFunction. Will now multiply that by 2."}
- multiplyFunction:
    call: http.post
    args:
        url: https://us-central1-workflow-demo-12-16.cloudfunctions.net/multiply # instead of us-central1-workflow-demo-12-16, use your {region-projectID}
        body:
            input: ${randomgenResult.body.random}
    result: multiplyResult
- logarithmFunction:
    call: http.get
    args:
        url: https://api.mathjs.org/v4/
        query:
            expr: ${"log(" + string(multiplyResult.body.multiplied) + ")"} # natural logarithm (ln) of the multiplied number
    result: logarithmResult
- returnResult:
    return: ${logarithmResult}
```

From here on, it gets rather complex and you'll need some Cloud Run and Docker knowledge. Continue if you really want to.

## Deploy a Cloud Run Service

In the last part, finalize the workflow with a call to a private Cloud Run service. This means that the workflow needs to be authenticated to call the Cloud Run service.

The Cloud Run service returns the math.floor of the passed in number.

Create and navigate to a directory for the service code:

```bash
mkdir ~/floor
cd ~/floor
```

Create an app.py file in the directory with the following contents:

```python
import json
import logging
import os
import math

from flask import Flask, request

app = Flask(__name__)

@app.route('/', methods=['POST'])
def handle_post():
    content = json.loads(request.data)
    input = float(content['input'])
    return f"{math.floor(input)}", 200

if __name__ != '__main__':
    # Redirect Flask logs to Gunicorn logs
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    app.logger.info('Service started...')
else:
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 8080))) 
```
    
Cloud Run deploys containers, so you need a Dockerfile and your container needs to bind to 0.0.0.0 and PORT env variable, hence the code above.

When it receives an HTTP request, this function extracts the input from the JSON body, calls math.floor and returns the result back to the caller.

In the same directory, create the following Dockerfile:

```dockerfile
# Use an official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.12-slim

# Install production dependencies.
RUN pip install Flask gunicorn

# Copy local code to the container image.
WORKDIR /app
COPY . .

# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
CMD exec gunicorn --bind 0.0.0.0:8080 --workers 1 --threads 8 app:app
```

Build the container:

```bash
export SERVICE_NAME=floor
gcloud builds submit --tag gcr.io/${GOOGLE_CLOUD_PROJECT}/${SERVICE_NAME}
```
Once the container is built, deploy to Cloud Run. Notice the no-allow-unauthenticated flag. This makes sure the service only accepts authenticated calls:

```bash
gcloud run deploy ${SERVICE_NAME} \
  --image gcr.io/${GOOGLE_CLOUD_PROJECT}/${SERVICE_NAME} \
  --platform managed \
  --no-allow-unauthenticated
```

Make sure to **copy the Service URL**, e.g. Service URL: https://floor-55xvrbnnwa-uc.a.run.app
Once deployed, the service is ready for the workflow.

## Connect the Cloud Run service
Before you can configure Workflows to call the private Cloud Run service, you need to create a service account for Workflows to use:

```bash
export SERVICE_ACCOUNT=workflows-sa
gcloud iam service-accounts create ${SERVICE_ACCOUNT}
```

Grant run.invoker role to the service account. This will allow the service account to call authenticated Cloud Run services:

```bash
gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT} \
    --member "serviceAccount:${SERVICE_ACCOUNT}@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com" \
    --role "roles/run.invoker" 
```
Also grant logging entries creation permission:
```bash
gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT} \
    --member "serviceAccount:${SERVICE_ACCOUNT}@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com" \
    --role "roles/logging.logWriter"
```

Update the workflow definition in workflow.yaml to include the Cloud Run service. Notice how you are also including an
auth field to make sure Workflows passes in the authentication token in its calls to the Cloud Run service:

Make sure you replace the url values with the actual urls of your functions as well as the Cloud Run Service URL.

```yaml
- randomgenFunction:
    call: http.get
    args:
        url: https://us-central1-workflow-demo-12-16.cloudfunctions.net/randomgen # instead of us-central1-workflow-demo-12-16, use your {region-projectID}  
    result: randomgenResult
- logRandomgenResult:
    call: sys.log
    args:
      severity: "INFO"
      text: ${"Received random number " + randomgenResult.body.random +" from randomgenFunction. Will now multiply that by 2."}
- multiplyFunction:
    call: http.post
    args:
        url: https://us-central1-workflow-demo-12-16.cloudfunctions.net/multiply # instead of us-central1-workflow-demo-12-16, use your {region-projectID}
        body:
            input: ${randomgenResult.body.random}
    result: multiplyResult
- logarithmFunction:
    call: http.get
    args:
        url: https://api.mathjs.org/v4/
        query:
            expr: ${"log(" + string(multiplyResult.body.multiplied) + ")"} # natural logarithm (ln) of the multiplied number
    result: logarithmResult
- floorFunction:
    call: http.post
    args:
      url: https://floor-55xvrbnnwa-uc.a.run.app # replace by your actual Cloud Run Service URL
        auth:
            type: OIDC
        body:
            input: ${logarithmResult.body}
    result: floorResult
- returnResult:
    return: ${floorResult}
```

Update the workflow. This time passing in the service-account:

```bash
gcloud workflows deploy workflow \
    --source=workflow.yaml \
    --service-account=${SERVICE_ACCOUNT}@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com
```
Execute the workflow:

```bash
gcloud workflows execute workflow
```

In a few seconds, you can take a look at the workflow execution to see the result:

gcloud workflows executions describe <your-execution-id> --workflow workflow
The output will include an integer result and state like:

```txt
result: '{"body":"5","code":200 ... } 
```
