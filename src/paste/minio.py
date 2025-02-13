import io
import uuid
from typing import Optional

from minio import Minio
from minio.error import S3Error

from .config import get_settings

client = Minio(
    get_settings().MINIO_CLIENT_LINK,
    access_key=get_settings().MINIO_ACCESS_KEY,
    secret_key=get_settings().MINIO_SECRET_KEY,
    secure=True,
)


def get_object_data(
    object_name: str, bucket_name: str = get_settings().MINIO_BUCKET_NAME
) -> str | None:
    response = None
    data = None
    try:
        response = client.get_object(bucket_name, object_name)
        data = response.read()
    except S3Error as exc:
        raise Exception(f"error occured.", exc)
    except Exception as exc:
        raise FileNotFoundError(
            f"Failed to retrieve file '{object_name}' from bucket '{bucket_name}': {exc}"
        )
    finally:
        if response:
            response.close()
            response.release_conn()

    return data.decode("utf-8")


def post_object_data(
    object_data: str,
    object_name: Optional[str] = None,
    bucket_name: str = get_settings().MINIO_BUCKET_NAME,
) -> str:
    try:
        if not object_name:
            object_name = str(uuid.uuid4())

        data_bytes = object_data.encode("utf-8")
        data_length = len(data_bytes)

        client.put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            data=io.BytesIO(data_bytes),
            length=data_length,
            content_type="text/plain",
        )

        # Generate the object URL using the proper method
        object_url = client.get_presigned_url(
            "GET",
            bucket_name=bucket_name,
            object_name=object_name,
        )
        return object_url
    except S3Error as exc:
        raise Exception(
            f"Failed to upload file '{object_name}' to bucket '{bucket_name}': {exc}"
        )


def post_object_data_as_file(
    source_file_path: str,
    object_name: Optional[str] = None,
    bucket_name: str = get_settings().MINIO_BUCKET_NAME,
) -> None:
    try:
        if not object_name:
            object_name = str(uuid.uuid4())

        client.fput_object(bucket_name, object_name, source_file_path)
    except S3Error as exc:
        raise Exception(
            f"Failed to upload file '{object_name}' to bucket '{bucket_name}': {exc}"
        )


def delete_object_data(
    object_name: str, bucket_name: str = get_settings().MINIO_BUCKET_NAME
) -> None:
    try:
        client.remove_object(bucket_name, object_name)
    except S3Error as exc:
        raise Exception(
            f"Failed to delete file '{object_name}' from bucket '{bucket_name}': {exc}"
        )
