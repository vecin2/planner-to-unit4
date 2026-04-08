class FabricFileOperations:
    def __init__(self, fs):
        self.fs = fs  # notebookutils.fs

    def exists(self, path: str) -> bool:
        return self.fs.exists(path)

    def move(self, source: str, destination: str) -> None:
        parent = "/".join(destination.split("/")[:-1])
        self.fs.mkdirs(parent)
        self.fs.mv(source, destination, True)
