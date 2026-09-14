import os
import shutil
import hashlib
import zipfile
import tarfile
from pathlib import Path
from typing import Union, Optional, List

class SuperPath:
    def __init__(self, path: Union[str, Path]):
        self._path = Path(path).resolve()

    @property
    def path(self) -> Path:
        return self._path

    @property
    def name(self) -> str:
        return self._path.name

    @property
    def ext(self) -> str:
        return self._path.suffix

    @property
    def parent(self) -> Path:
        return self._path.parent

    def exists(self) -> bool:
        return self._path.exists()

    def is_dir(self) -> bool:
        return self._path.is_dir()

    def is_file(self) -> bool:
        return self._path.is_file()

    def size(self) -> int:
        if self.is_file():
            return self._path.stat().st_size
        elif self.is_dir():
            return sum(f.stat().st_size for f in self._path.rglob('*') if f.is_file())
        return 0

    def hash(self, algorithm: str = "sha256", chunk_size: int = 65536) -> str:
        hasher = getattr(hashlib, algorithm)()
        with open(self._path, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()

    def list_files(self) -> List["SuperPath"]:
        if not self.is_dir():
            return []
        return [SuperPath(p) for p in self._path.rglob("*") if p.is_file()]

    def zip(self, destination: Optional[Union[str, Path]] = None) -> "SuperPath":
        dest = Path(destination) if destination else self._path.with_suffix(".zip")
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            if self.is_file():
                zf.write(self._path, self._path.name)
            else:
                for file_path in self._path.rglob("*"):
                    zf.write(file_path, file_path.relative_to(self._path.parent))
        return SuperPath(dest)

    def unzip(self, destination: Optional[Union[str, Path]] = None) -> "SuperPath":
        dest_dir = Path(destination) if destination else self._path.parent / self._path.stem
        dest_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(self._path, "r") as zf:
            zf.extractall(dest_dir)
        return SuperPath(dest_dir)

    def tar(self, destination: Optional[Union[str, Path]] = None, mode: str = "w:gz") -> "SuperPath":
        ext_map = {"w": ".tar", "w:gz": ".tar.gz", "w:bz2": ".tar.bz2"}
        ext = ext_map.get(mode, ".tar.gz")
        dest = Path(destination) if destination else self._path.with_name(self._path.name + ext)
        with tarfile.open(dest, mode) as tf:
            tf.add(self._path, arcname=self._path.name)
        return SuperPath(dest)

    def untar(self, destination: Optional[Union[str, Path]] = None) -> "SuperPath":
        dest_dir = Path(destination) if destination else self._path.parent / self._path.name.split('.')[0]
        dest_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(self._path, "r:*") as tf:
            tf.extractall(dest_dir)
        return SuperPath(dest_dir)

    def __str__(self) -> str:
        return str(self._path)

def super_path(path: Union[str, Path]) -> SuperPath:
    return SuperPath(path)
