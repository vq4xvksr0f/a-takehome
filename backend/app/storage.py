"""Object storage port + boto3 adapter (MinIO / S3-compatible).

Two clients are used on purpose: `put`/`delete` go through the internal
endpoint (`S3_ENDPOINT_URL`, e.g. http://minio:9000 on the Compose network),
while pre-signed URLs are generated with a client bound to
`S3_PUBLIC_ENDPOINT` (e.g. http://localhost:9000) so the host embedded in the
signature is one the browser can actually reach.
"""

from abc import ABC, abstractmethod
from typing import BinaryIO

import boto3
from botocore.client import Config as BotoConfig

from .config import get_settings


class ObjectStore(ABC):
    @abstractmethod
    def put(self, fileobj: BinaryIO, key: str, content_type: str) -> None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    @abstractmethod
    def presigned_get_url(self, key: str, expires: int) -> str: ...


class BotoObjectStore(ObjectStore):
    def __init__(self) -> None:
        settings = get_settings()
        common = dict(
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            # Path-style addressing is required by MinIO and harmless on S3.
            config=BotoConfig(s3={"addressing_style": "path"}),
        )
        self._bucket = settings.S3_BUCKET
        self._client = boto3.client(
            "s3", endpoint_url=settings.S3_ENDPOINT_URL, **common
        )
        self._signing_client = boto3.client(
            "s3", endpoint_url=settings.S3_PUBLIC_ENDPOINT, **common
        )

    def put(self, fileobj: BinaryIO, key: str, content_type: str) -> None:
        self._client.upload_fileobj(
            fileobj, self._bucket, key, ExtraArgs={"ContentType": content_type}
        )

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def presigned_get_url(self, key: str, expires: int) -> str:
        return self._signing_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires,
        )
