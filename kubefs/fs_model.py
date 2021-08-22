import logging
import os
import stat
import time
from typing import Dict, Iterable, List, Optional, Union

from akube.cluster_facade import SyncClusterFacade
from akube.model.selector import ObjectSelector
from kube.config import Context, KubeConfigCollection

logger = logging.getLogger("fs_model")


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
    def __init__(self) -> None:

        self.name: str = ""

        # lazy attributes (different atts will be set depending on the derived
        # class)
        self.config: Optional[KubeConfigCollection] = None
        self.context: Optional[Context] = None
        self.facade: Optional[SyncClusterFacade] = None
        self.selector: Optional[ObjectSelector] = None

    def get_attributes(self) -> Dict[str, Union[int, float]]:
        raise NotImplemented


class Directory(AbstractEntry):
    def __init__(
        self, *, payload: Payload, entries: Iterable[AbstractEntry] = None
    ) -> None:
        self.name = payload.name
        self._entries = entries or []

        self._lazy_entries: List[AbstractEntry] = []
        self._lazy_entries_loaded_time = 0
        self._lazy_entries_lifetime = 60  # in seconds

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

    @property
    def lazy_entries(self):
        if not self._lazy_entries:
            return []

        elapsed = time.time() - self._lazy_entries_loaded_time
        if elapsed > self._lazy_entries_lifetime:
            logger.debug(
                "dir %r cached entries expired (%ds elapsed > %ds lifetime)",
                self.name,
                elapsed,
                self._lazy_entries_lifetime,
            )
            return []

        logger.debug(
            "dir %r returning cached entries (%ds since last load < %ds lifetime)",
            self.name,
            elapsed,
            self._lazy_entries_lifetime,
        )
        return self._lazy_entries

    @lazy_entries.setter
    def lazy_entries(self, entries):
        self._lazy_entries = entries
        self._lazy_entries_loaded_time = time.time()

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
