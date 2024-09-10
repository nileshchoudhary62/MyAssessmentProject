""" This script creates an AWS Cloud Development Kit (CDK) stack to deploy a basic AWS infrastructure setup, including an Amazon Elastic Kubernetes Service (EKS) cluster, an AWS Lambda function, and IAM policies.

Modules:
- aws_cdk: The core CDK constructs and classes.
- constructs: These are the constructs that define the CDK stack.
- aws_cdk.lambda_layer_kubectl_v29 is a CDK construct for the Kubernetes kubectl binary.

Classes: - My AssessmentProjectStack is a CDK stack that contains the following resources:
  - A VPC with public and private subnets.
  - An EKS cluster containing a managed node group.
  - IAM roles and policies for the EKS cluster and node groups.
  - An AWS Lambda function that serves as a custom resource.
  - Use SSM Parameter Store to configure the environment. """

from aws_cdk import (
    Stack,
    Duration,
    aws_ec2 as ec2,
    aws_eks as eks,
    aws_iam as iam,
    aws_ssm as ssm,
    aws_lambda as _lambda,
    CfnOutput,
    Tags,
)
from constructs import Construct
from aws_cdk.lambda_layer_kubectl_v29 import KubectlV29Layer


class MyAssessmentProjectStack(Stack):
    """
    A CDK stack that deploys an EKS cluster along with associated resources such as VPC, IAM roles,
    Lambda function, and SSM parameters.

    Args:
        scope (Construct): The scope in which this construct is defined.
        construct_id (str): The ID of this construct.
        **kwargs: Additional keyword arguments to pass to the Stack constructor.
    """

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """
        Initializes the stack by setting up resources including VPC, EKS cluster, IAM roles,
        Lambda function, and SSM parameter.

        Args:
            scope (Construct): The scope in which this construct is defined.
            construct_id (str): The ID of this construct.
            **kwargs: Additional keyword arguments to pass to the Stack constructor.
        """
        super().__init__(scope, construct_id, **kwargs)

        # Define a VPC with public and private subnets
        vpc = ec2.Vpc(
            self,
            "eks-vpc",
            ip_addresses=ec2.IpAddresses.cidr("10.3.0.0/16"),
            max_azs=3,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="PublicSubnet", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="PrivateSubnet",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24,
                ),
            ],
        )

        # Tag public subnets for EKS ELB access
        for subnet in vpc.public_subnets:
            Tags.of(subnet).add("kubernetes.io/role/elb", "1")

        # Tag private subnets for internal load balancers
        for subnet in vpc.private_subnets:
            Tags.of(subnet).add("kubernetes.io/role/internal-elb", "1")

        # Create IAM role for the EKS cluster with necessary policies
        eks_cluster_role = iam.Role(
            self,
            "EksClusterRole",
            assumed_by=iam.ServicePrincipal("eks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonEKSClusterPolicy"
                ),
            ],
        )

        # Create IAM role for the EKS node group with specific managed policies
        eks_nodegroup_role = iam.Role(
            self,
            "EksNodeGroupRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonEC2ContainerRegistryReadOnly"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonEKS_CNI_Policy"),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonEKSWorkerNodePolicy"
                ),
            ],
        )

        # Define the EKS cluster with public access enabled
        cluster = eks.Cluster(
            self,
            "MyCluster",
            vpc=vpc,
            version=eks.KubernetesVersion.V1_29,
            role=eks_cluster_role,
            default_capacity=0,  # No default worker nodes
            kubectl_layer=KubectlV29Layer(self, "KubectlLayer"),  # Add kubectl layer
            endpoint_access=eks.EndpointAccess.PUBLIC_AND_PRIVATE,  # Public access
        )

        # Add a managed node group to the EKS cluster
        cluster.add_nodegroup_capacity(
            "ManagedNodeGroup",
            desired_size=2,
            min_size=2,
            max_size=3,
            instance_types=[ec2.InstanceType("t2.small")],
            node_role=eks_nodegroup_role,
        )

        # Define an SSM parameter for environment configuration
        env_value = "development"
        env_param = ssm.StringParameter(
            self,
            "PlatformAccountEnv",
            parameter_name="/platform/account/env",
            string_value=env_value,
            description="Environment parameter for platform account",
        )

        # Create IAM role for Lambda function used as a custom resource
        lambda_role = iam.Role(
            self,
            "CustomResourceFunctionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
        )
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[env_param.parameter_arn],
                effect=iam.Effect.ALLOW,
            )
        )

        # Create Lambda function
        lambda_function = _lambda.Function(
            self,
            "CustomResourceFunction",
            runtime=_lambda.Runtime.PYTHON_3_9,
            handler="lambda_function.handler",
            code=_lambda.Code.from_asset(
                "lambda_function"
            ),  # Path to Lambda function code
            timeout=Duration.seconds(30),
            role=lambda_role,
        )

        # Output the Lambda function ARN
        CfnOutput(
            self,
            "CustomResourceFunctionArn",
            value=lambda_function.function_arn,
            description="The ARN of the custom resource Lambda function",
        )

        # Output the EKS cluster name
        CfnOutput(
            self,
            "EksClusterName",
            value=cluster.cluster_name,
            description="The name of the EKS cluster",
        )
# Assuming from the instructions, we do not want to integrate the Helm directly to the EKS cluster so I am commenting the below task and will use shell script to do this. Keeping here the code as a reference.
# # Add NGINX ingress using Helm
#         eks.HelmChart(
#             self, "NginxIngress",
#             cluster=cluster,
#             chart="ingress-nginx",
#             repository="https://kubernetes.github.io/ingress-nginx",
#             namespace="ingress-nginx",
#             values=helm_values
#         )