import shutil
from pathlib import Path


class LocalFileOperations:
    def exists(self, path: str) -> bool:
        return Path(path).exists()

    def move(self, source: str, destination: str) -> None:
        Path(destination).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(source, destination)
