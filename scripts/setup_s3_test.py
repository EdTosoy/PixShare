"""Provision only a dedicated local test bucket; never AWS or application buckets."""

import json
import os
from urllib.parse import urlsplit

from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.storage.s3 import S3Storage


def main() -> None:
    settings = get_settings()
    if (
        os.environ.get("S3_INTEGRATION_TEST") != "1"
        or not settings.s3_endpoint_url
        or urlsplit(settings.s3_endpoint_url).hostname not in {"127.0.0.1", "localhost", "minio"}
        or not settings.s3_bucket.endswith("-test")
        or not settings.s3_access_key_id
        or not settings.s3_secret_access_key
    ):
        raise SystemExit("Refusing setup outside an explicitly configured dedicated local test bucket")
    storage = S3Storage(settings)
    try:
        _ = storage.client.head_bucket(Bucket=storage.bucket)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") not in {"404", "NoSuchBucket"}:
            raise SystemExit("Cannot access local test bucket; SDK details withheld") from None
        _ = storage.client.create_bucket(Bucket=storage.bucket)
    policy = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": "*", "Action": ["s3:GetObject"],
                       "Resource": [f"arn:aws:s3:::{storage.bucket}/phase9/*/original.*",
                                    f"arn:aws:s3:::{storage.bucket}/phase9/*/variants/*.webp"]}],
    }
    _ = storage.client.put_bucket_policy(Bucket=storage.bucket, Policy=json.dumps(policy))
    print("Dedicated local bucket ready: anonymous image GET only; no anonymous list/write/delete/manifest access")


if __name__ == "__main__":
    main()
