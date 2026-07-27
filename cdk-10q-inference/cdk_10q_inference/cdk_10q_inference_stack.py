from aws_cdk import (
    Stack,
    Duration,
    aws_iam as iam,
    aws_lambda as _lambda,
)
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from constructs import Construct


class Cdk10QInferenceStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        inference_lambda = PythonFunction(
            self, "TenQInferenceFunction",
            entry="lambda-10q-inference",
            index="handler.py",
            handler="lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(60),
        )

        inference_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["*"],
            )
        )