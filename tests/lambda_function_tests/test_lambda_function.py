# Importing necessary modules
import json
import boto3
from moto import mock_aws  # For mocking AWS services
import pytest
import sys
import os

# Adding the parent directory of the current file to the system path
# This allows the import of modules from sibling directories
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Importing the handler function from the lambda_function module
from lambda_function.lambda_function import handler


# Fixture to create a mocked SSM (AWS Systems Manager) client
@pytest.fixture
def ssm_client():
    with mock_aws():  # Use the mock AWS environment provided by the moto library
        client = boto3.client(
            "ssm", region_name="us-east-1"
        )  # Create a mocked SSM client
        yield client  # Provide the client to the test functions


# Test case for the handler function in the 'development' environment
def test_handler_development(ssm_client):
    # Mocking an SSM parameter to indicate the environment is 'development'
    ssm_client.put_parameter(
        Name="/platform/account/env", Value="development", Type="String"
    )

    # Preparing empty event and context objects
    event = {}
    context = {}

    # Calling the handler function
    response = handler(event, context)

    # Expected Helm values for the 'development' environment
    expected_helm_values = {"controller": {"replicaCount": 1}}

    # Asserting that the response status is "SUCCESS"
    assert response["Status"] == "SUCCESS"
    # Asserting that the Helm values in the response match the expected values
    assert json.loads(response["Data"]["HelmValues"]) == expected_helm_values


# Test case for the handler function in the 'production' environment
def test_handler_production(ssm_client):
    # Mocking an SSM parameter to indicate the environment is 'production'
    ssm_client.put_parameter(
        Name="/platform/account/env", Value="production", Type="String"
    )

    # Preparing empty event and context objects
    event = {}
    context = {}

    # Calling the handler function
    response = handler(event, context)

    # Expected Helm values for the 'production' environment
    expected_helm_values = {"controller": {"replicaCount": 2}}

    # Asserting that the response status is "SUCCESS"
    assert response["Status"] == "SUCCESS"
    # Asserting that the Helm values in the response match the expected values
    assert json.loads(response["Data"]["HelmValues"]) == expected_helm_values


# Test case for the handler function when an exception is expected
def test_handler_exception(ssm_client):
    # Preparing empty event and context objects
    event = {}
    context = {}

    # Calling the handler function
    response = handler(event, context)

    # Asserting that the response status is "FAILED"
    assert response["Status"] == "FAILED"
    # Asserting that the response contains a reason for failure
    assert "Reason" in response
