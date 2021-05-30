from typing import Iterable, Dict, List, Union
import stat
import time
import os


class Payload:
    """A simple wrapper type for all the attributes that a File / Directory
    needs to have. This avoids having to make all of these parameters to the
    __init__() method of File / Directory, which are also subclassed a lot."""

    def __init__(
        self,
        *,
        name: str,
        data: bytes = b"",
        ctime: float = None,
        mtime: float = None,
        atime: float = None,
        uid: int = None,
        gid: int = None
    ) -> None:
        self.name = name

        self.data = data
        self.size = len(self.data)

        now = time.time()
        self.ctime = ctime or now
        self.mtime = mtime or now
        self.atime = atime or now

        self.uid = uid or os.getuid()
        self.gid = gid or os.getgid()


class AbstractEntry:
    def get_attributes(self) -> Dict[str, Union[int, float]]:
        raise NotImplemented


class Directory(AbstractEntry):
    def __init__(
        self, *, payload: Payload, entries: Iterable[AbstractEntry] = None
    ) -> None:
        self.name = payload.name
        self._entries = entries or []
        self._lazy_entries = []  # lazy

        self.atts = dict(
            st_mode=(stat.S_IFDIR | 0o755),
            st_nlink=2,
            st_size=0,
            st_ctime=payload.ctime,
            st_mtime=payload.mtime,
            st_atime=payload.atime,
            st_uid=payload.uid,
            st_gid=payload.gid,
        )

    def get_entries(self) -> Iterable[AbstractEntry]:
        return self._entries

    def get_attributes(self):
        return self.atts

    def get_entry_names(self) -> List[str]:
        names = [entry.name for entry in self.get_entries()]
        return names

    def get_entry_by_name(self, entry_name: str) -> AbstractEntry:
        for entry in self.get_entries():
            if entry.name == entry_name:
                return entry


class File(AbstractEntry):
    def __init__(self, *, payload: Payload) -> None:
        self.name = payload.name
        self.data = payload.data

        self.atts = dict(
            st_mode=(stat.S_IFREG | 0o644),
            st_nlink=1,
            st_size=payload.size,
            st_ctime=payload.ctime,
            st_mtime=payload.mtime,
            st_atime=payload.atime,
            st_uid=payload.uid,
            st_gid=payload.gid,
        )

    def get_attributes(self):
        return self.atts

    def read(self, size: int, offset: int) -> bytes:
        return self.data[offset : offset + size]
