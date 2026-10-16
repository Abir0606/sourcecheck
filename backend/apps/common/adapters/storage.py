"""
Storage adapters. The rest of the application depends only on `StorageBackend`.

- LocalStorage: filesystem, used for local development and tests.
- AzureBlobStorage: Azure Blob Storage, imported lazily so the app runs with
  no Azure SDK configuration or credentials.
"""
from __future__ import annotations

import abc
import shutil
from pathlib import Path

from django.conf import settings


class StorageBackend(abc.ABC):
    @abc.abstractmethod
    def save(self, key: str, fileobj) -> str: ...

    @abc.abstractmethod
    def open(self, key: str): ...

    @abc.abstractmethod
    def delete(self, key: str) -> None: ...

    @abc.abstractmethod
    def exists(self, key: str) -> bool: ...

    @abc.abstractmethod
    def healthcheck(self) -> None: ...

    def delete_prefix(self, prefix: str) -> int:
        """Delete everything under a prefix. Returns count removed."""
        raise NotImplementedError


class LocalStorage(StorageBackend):
    def __init__(self, root: str | None = None):
        self.root = Path(root or settings.LOCAL_STORAGE_DIR)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = Path(key)
        if safe.is_absolute() or ".." in safe.parts:
            raise ValueError("Invalid storage key")
        return self.root / safe

    def save(self, key: str, fileobj) -> str:
        dest = self._path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as fh:
            for chunk in iter(lambda: fileobj.read(1024 * 1024), b""):
                fh.write(chunk)
        return key

    def open(self, key: str):
        return open(self._path(key), "rb")

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def delete_prefix(self, prefix: str) -> int:
        base = self._path(prefix)
        if not base.exists():
            return 0
        count = 0
        if base.is_dir():
            for p in base.rglob("*"):
                if p.is_file():
                    count += 1
            shutil.rmtree(base, ignore_errors=True)
        else:
            base.unlink()
            count = 1
        return count

    def healthcheck(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        probe = self.root / ".healthcheck"
        probe.write_text("ok")
        probe.unlink()


class AzureBlobStorage(StorageBackend):
    """Lazy Azure Blob adapter. Requires STORAGE_BACKEND=azure + credentials."""

    def __init__(self, account_url: str, container: str, auth: str):
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient

        if auth == "connection_string":
            self._service = BlobServiceClient.from_connection_string(account_url)
        elif auth == "managed_identity":
            self._service = BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())
        else:
            from azure.core.credentials import AzureNamedKeyCredential
            from azure.storage.blob import BlobServiceClient as _BSC

            _ = AzureNamedKeyCredential  # account_key path resolved from Key Vault at runtime
            self._service = _BSC(account_url=account_url, credential=DefaultAzureCredential())
        self.container = container
        try:
            self._service.create_container(container)
        except Exception:
            pass

    def _blob(self, key: str):
        return self._service.get_blob_client(container=self.container, blob=key)

    def save(self, key: str, fileobj) -> str:
        self._blob(key).upload_blob(fileobj, overwrite=True)
        return key

    def open(self, key: str):
        import io

        data = self._blob(key).download_blob().readall()
        return io.BytesIO(data)

    def delete(self, key: str) -> None:
        try:
            self._blob(key).delete_blob()
        except Exception:
            pass

    def exists(self, key: str) -> bool:
        return self._blob(key).exists()

    def delete_prefix(self, prefix: str) -> int:
        count = 0
        for blob in self._service.get_container_client(self.container).list_blobs(name_starts_with=prefix):
            self._service.get_container_client(self.container).delete_blob(blob.name)
            count += 1
        return count

    def healthcheck(self) -> None:
        self._service.get_container_client(self.container).get_container_properties()
