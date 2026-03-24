import io
import uuid
from typing import Optional

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from .config import get_settings

client = boto3.client(
    "s3",
    endpoint_url=get_settings().MINIO_CLIENT_LINK,
    aws_access_key_id=get_settings().MINIO_ACCESS_KEY,
    aws_secret_access_key=get_settings().MINIO_SECRET_KEY,
    config=Config(signature_version="s3v4"),
    region_name="us-east-1",
)


def create_bucket_if_not_exists(bucket_name: str = get_settings().MINIO_BUCKET_NAME) -> None:
    try:
        client.create_bucket(Bucket=bucket_name)
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "BucketAlreadyOwnedByYou":
            raise


def get_object_data(object_name: str, bucket_name: str = get_settings().MINIO_BUCKET_NAME) -> str | None:
    response = None
    data = None
    try:
        response = client.get_object(Bucket=bucket_name, Key=object_name)
        data = response["Body"].read()
    except ClientError as exc:
        raise Exception("error occured.", exc)
    except Exception as exc:
        raise FileNotFoundError(f"Failed to retrieve file '{object_name}' from bucket '{bucket_name}': {exc}")
    return data.decode("utf-8")


def post_object_data(
    object_data: str,
    object_name: Optional[str] = None,
    bucket_name: str = get_settings().MINIO_BUCKET_NAME,
) -> str | None:
    try:
        if not object_name:
            object_name = str(uuid.uuid4())

        data_bytes = object_data.encode("utf-8")
        data_length = len(data_bytes)

        client.put_object(
            Bucket=bucket_name,
            Key=object_name,
            Body=io.BytesIO(data_bytes),
            ContentLength=data_length,
            ContentType="text/plain",
        )

        return object_name
    except ClientError as exc:
        raise Exception(f"Failed to upload file '{object_name}' to bucket '{bucket_name}': {exc}")


def post_object_data_as_file(
    source_file_path: str,
    object_name: Optional[str] = None,
    bucket_name: str = get_settings().MINIO_BUCKET_NAME,
) -> str | None:
    try:
        if not object_name:
            object_name = str(uuid.uuid4())

        client.upload_file(source_file_path, bucket_name, object_name)
        return object_name
    except ClientError as exc:
        raise Exception(f"Failed to upload file '{object_name}' to bucket '{bucket_name}': {exc}")


def delete_object_data(object_name: str, bucket_name: str = get_settings().MINIO_BUCKET_NAME) -> None:
    try:
        client.delete_object(Bucket=bucket_name, Key=object_name)
    except ClientError as exc:
        raise Exception(f"Failed to delete file '{object_name}' from bucket '{bucket_name}': {exc}")
