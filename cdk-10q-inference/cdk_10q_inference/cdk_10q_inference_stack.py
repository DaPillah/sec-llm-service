from aws_cdk import (
    Stack,
    Duration,
    aws_iam as iam,
    aws_lambda as _lambda,
)
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from constructs import Construct
from aws_cdk import aws_ecr_assets as ecr_assets


class Cdk10QInferenceStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- Core Lambda: the four-step inference pipeline ---
        inference_lambda = PythonFunction(
            self, "TenQInferenceFunction",
            entry="lambda-10q-inference",
            index="handler.py",
            handler="core_handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(60),
        )

        inference_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["*"],
            )
        )

        # --- RAG Lambda: chunk, embed, retrieve, generate ---
        rag_lambda = _lambda.DockerImageFunction(
            self, "RagInferenceFunction",
            code=_lambda.DockerImageCode.from_image_asset(
                "lambda-rag",
                platform=ecr_assets.Platform.LINUX_AMD64,
            ),
            architecture=_lambda.Architecture.X86_64,
            timeout=Duration.seconds(120),
            memory_size=512,
            environment={
                "MODEL_ID": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
                "EMBEDDING_MODEL_ID": "amazon.titan-embed-text-v2:0",
            },
        )

        rag_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["*"],
            )
        )

        # --- Edge Lambda: identity, validation, HTTP translation, routing ---
        edge_lambda = PythonFunction(
            self, "EdgeFunction",
            entry="lambda-edge",
            index="handler.py",
            handler="edge_handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(29),
            environment={
                "CORE_FUNCTION_NAME": inference_lambda.function_name,
                "RAG_FUNCTION_NAME": rag_lambda.function_name,
            },
        )

        inference_lambda.grant_invoke(edge_lambda)
        rag_lambda.grant_invoke(edge_lambda)