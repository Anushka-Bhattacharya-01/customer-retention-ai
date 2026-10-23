"""Small helpers to move model files to and from S3 (used only when S3 settings are given)."""
from urllib.parse import urlparse


def _split(s3_uri: str):
    parsed = urlparse(s3_uri)
    if parsed.scheme != "s3":
        raise ValueError(f"Not an S3 URI: {s3_uri}")
    return parsed.netloc, parsed.path.lstrip("/")


def upload(local_path: str, s3_uri: str) -> None:
    import boto3
    bucket, key = _split(s3_uri)
    boto3.client("s3").upload_file(local_path, bucket, key)


def download(s3_uri: str, local_path: str) -> None:
    import boto3
    bucket, key = _split(s3_uri)
    boto3.client("s3").download_file(bucket, key, local_path)
