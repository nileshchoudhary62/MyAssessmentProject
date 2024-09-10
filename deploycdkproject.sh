#!/bin/bash

# Script for deploying a CDK stack, retrieving Lambda function output, and managing Helm charts

# Variables
STACK_NAME="MyAssessmentProjectStack"          # Name of the CDK stack
HELM_CHART_NAME="ingress-nginx"                 # Name of the Helm chart to install/upgrade
HELM_REPO_NAME="ingress-nginx"                  # Helm repository name
HELM_REPO_URL="https://kubernetes.github.io/ingress-nginx"  # URL of the Helm repository
OUTPUT_KEY="CustomResourceFunctionArn"          # Output key for Lambda function ARN from the stack
CLUSTER_NAME_OUTPUT_KEY="EksClusterName"        # Output key for EKS cluster name from the stack
VALUES_FILE="helm-values.yaml"                  # File to save Helm values

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt              # Install project dependencies
pip install -r requirements-dev.txt          # Install development dependencies

# Run unit tests before deploying
echo "Running unit tests with pytest..."
pytest tests/lambda_function_tests/test_lambda_function.py  # Execute unit tests

# Deploy the CDK stack
echo "Deploying CDK stack..."
cdk synth                                   # Generate the CloudFormation template
cdk deploy                                  # Deploy the stack

# Check if the deployment was successful
if [ $? -ne 0 ]; then
    echo "CDK deployment failed. Exiting."
    exit 1
fi

# Retrieve the Lambda function ARN
echo "Retrieving Lambda function ARN..."
LAMBDA_ARN=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query "Stacks[0].Outputs[?OutputKey=='$OUTPUT_KEY'].OutputValue" \
    --output text)

if [ -z "$LAMBDA_ARN" ]; then
    echo "Failed to retrieve Lambda function ARN. Exiting."
    exit 1
fi

echo "Lambda ARN: $LAMBDA_ARN"

# Retrieve the EKS cluster name
echo "Retrieving EKS cluster name..."
CLUSTER_NAME=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query "Stacks[0].Outputs[?OutputKey=='$CLUSTER_NAME_OUTPUT_KEY'].OutputValue" \
    --output text)

if [ -z "$CLUSTER_NAME" ]; then
    echo "Failed to retrieve EKS cluster name. Exiting."
    exit 1
fi

echo "EKS Cluster Name: $CLUSTER_NAME"

# Update kubeconfig with the EKS cluster details
echo "Updating kubeconfig..."
aws eks --region us-east-1 update-kubeconfig --name $CLUSTER_NAME

# Invoke the Lambda function and capture the output
echo "Invoking Lambda function..."
aws lambda invoke --function-name $LAMBDA_ARN --payload '{}' output.json

# Check if the Lambda invocation was successful
if [ $? -ne 0 ]; then
    echo "Lambda function invocation failed. Exiting."
    exit 1
fi

# Print the content of the output.json for debugging
echo "Lambda output:"
cat output.json

# Retrieve Helm values from the Lambda function output
echo "Retrieving Helm values..."
# Extract HelmValues field from the JSON and parse the inner JSON string
HELM_VALUES=$(jq -r '.Data.HelmValues' output.json)

# Print the Helm values for debugging
echo "Helm Values:"
echo "$HELM_VALUES"

# Check if HelmValues was retrieved successfully
if [ -z "$HELM_VALUES" ] || [ "$HELM_VALUES" == "null" ]; then
    echo "Failed to retrieve HelmValues. Exiting."
    exit 1
fi

# Parse the HelmValues JSON to extract the replicaCount
REPLICA_COUNT=$(echo "$HELM_VALUES" | jq -r '.controller.replicaCount')

# Check if replica count was retrieved successfully
if [ -z "$REPLICA_COUNT" ]; then
    echo "Failed to retrieve replica count. Exiting."
    exit 1
fi

# Generate Helm values YAML file
cat <<EOF > $VALUES_FILE
controller:
  replicaCount: $REPLICA_COUNT
EOF

echo "Helm values saved to $VALUES_FILE."

# Check if Helm is installed; if not, install it
if ! command -v helm &> /dev/null; then
    echo "Helm not found. Installing Helm..."
    curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
    if [ $? -ne 0 ]; then
        echo "Helm installation failed. Exiting."
        exit 1
    fi
else
    echo "Helm is already installed."
fi

# Add the ingress-nginx Helm repository and update it
echo "Adding the Helm repository..."
helm repo add $HELM_REPO_NAME $HELM_REPO_URL
helm repo update

# Install or upgrade the ingress-nginx Helm chart
echo "Installing or upgrading the ingress-nginx Helm chart..."
helm upgrade --install $HELM_CHART_NAME $HELM_REPO_NAME/$HELM_CHART_NAME -f $VALUES_FILE

# Check if the Helm chart installation was successful
if [ $? -ne 0 ]; then
    echo "Helm chart installation failed. Exiting."
    exit 1
fi

echo "Ingress-nginx Helm chart installed successfully!"