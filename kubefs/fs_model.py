from typing import Iterable, Dict, Any, List
import stat
import time
import os


class Entry:
    def get_attributes(self) -> Dict[Any, Any]:
        raise NotImplemented


class Directory(Entry):
    def __init__(self, *, name: str, entries: Iterable[Entry] = None) -> None:
        self.name = name
        self.entries = entries or []

        self.ts_opened = time.time()
        self.uid = os.getuid()
        self.gid = os.getgid()

        self.atts = dict(
            st_mode=(stat.S_IFDIR | 0o755),
            st_nlink=2,
            st_size=0,
            st_ctime=self.ts_opened,
            st_mtime=self.ts_opened,
            st_atime=self.ts_opened,
            st_uid=self.uid,
            st_gid=self.gid,
        )

    def get_attributes(self):
        return self.atts

    def get_entry_names(self) -> List[str]:
        names = [entry.name for entry in self.entries]
        return names

    def get_entry_by_name(self, entry_name) -> Entry:
        for entry in self.entries:
            if entry.name == entry_name:
                return entry


class File(Entry):
    def __init__(self, *, name, contents: bytes = None) -> None:
        self.name = name
        self.contents = contents

        self.ts_opened = time.time()
        self.uid = os.getuid()
        self.gid = os.getgid()

        self.atts = dict(
            st_mode=(stat.S_IFREG | 0o644),
            st_nlink=1,
            st_size=len(contents),
            st_ctime=self.ts_opened,
            st_mtime=self.ts_opened,
            st_atime=self.ts_opened,
            st_uid=self.uid,
            st_gid=self.gid,
        )

    def get_attributes(self):
        return self.atts

    def read(self, size, offset) -> bytes:
        return self.contents[offset : offset + size]
