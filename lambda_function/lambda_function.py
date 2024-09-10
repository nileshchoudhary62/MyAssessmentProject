"""
This script defines an AWS Lambda function handler that interacts with AWS Systems Manager (SSM) 
to retrieve an environment parameter and determine the appropriate Helm values based on that environment.

Modules:
- boto3: AWS SDK for Python, used to interact with AWS services.
- json: Provides functions to work with JSON data.

Function:
- handler(event, context): 
    This function serves as the entry point for the Lambda function. It performs the following tasks:
    1. Retrieves an SSM parameter value to determine the environment.
    2. Sets Helm values based on the environment.
    3. Returns success with Helm values as a JSON string or failure with an error message.

Args:
    event (dict): The event data passed to the Lambda function.
    context (LambdaContext): The context object providing runtime information.

Returns:
    dict: A dictionary containing the status of the operation and the Helm values (if successful), or 
          an error message (if failed).
"""

import boto3
import json


def handler(event, context):
    """
    AWS Lambda function handler that retrieves an environment parameter from SSM and determines Helm values
    based on the environment.

    Args:
        event (dict): The event data passed to the Lambda function.
        context (LambdaContext): The context object providing runtime information.

    Returns:
        dict: A dictionary containing the status of the operation and the Helm values (if successful), or
              an error message (if failed).
    """
    ssm_client = boto3.client("ssm")
    param_name = "/platform/account/env"

    try:
        # Retrieve the parameter value from SSM
        response = ssm_client.get_parameter(Name=param_name)
        env_value = response["Parameter"]["Value"]
        print(env_value)

        # Determine Helm values based on environment
        helm_values = (
            {"controller": {"replicaCount": 1}}
            if env_value == "development"
            else {"controller": {"replicaCount": 2}}
        )

        # Return success with Helm values as JSON
        return {"Status": "SUCCESS", "Data": {"HelmValues": json.dumps(helm_values)}}

    except Exception as e:
        # Log the error and return failure status with error message
        print(f"Error: {str(e)}")
        return {"Status": "FAILED", "Reason": str(e)}
