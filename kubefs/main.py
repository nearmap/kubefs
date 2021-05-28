#!/usr/bin/env python
from kubefs.fs_model import Directory, File
from kubefs.fs_kubeconfig import KubeConfigUsersDir
from kubefs.kubeconfig import KubeConfigLoader
import logging
import os
import errno

import fuse

from kubefs import kubeconfig


class KubernetesFs(fuse.LoggingMixIn, fuse.Operations):
    _loader = KubeConfigLoader.get_instance()

    tree = Directory(
        name="",
        entries=[
            Directory(
                name="clusters",
                entries=[
                    Directory(name="cluster-1"),
                ],
            ),
            Directory(name="contexts"),
            KubeConfigUsersDir.create(name="users", loader=_loader),
        ],
    )

    constant_entries = [
        ".",
        "..",
    ]

    def __init__(self):
        self.basepath = os.sep

    def find_matching_entry(self, path):
        if path == os.sep:
            return self.tree

        # /clusters/cluster-1/pods/fst -> clusters/cluster-1/pods/fst
        _, relpath = path.split(self.basepath, 1)
        containing = self.tree

        # recurse up the tree until we find the entry in its containing dir
        while os.sep in relpath:
            # clusters/cluster-1/pods/fst -> (clusters, cluster-1/pods/fst)
            topdir, relpath = relpath.split(os.sep, 1)
            containing = containing.get_entry_by_name(topdir)

        if containing:
            entry = containing.get_entry_by_name(relpath)
            return entry

    def readdir(self, path, fh):
        entry = self.find_matching_entry(path)
        if not entry:
            raise fuse.FuseOSError(errno.ENOENT)

        constants = self.constant_entries
        provided = entry.get_entry_names()
        return constants + provided

    def getattr(self, path, fh=None):
        entry = self.find_matching_entry(path)
        if not entry:
            raise fuse.FuseOSError(errno.ENOENT)

        return entry.get_attributes()

    def read(self, path, size, offset, fh):
        entry = self.find_matching_entry(path)
        if not entry:
            raise fuse.FuseOSError(errno.EIO)

        return entry.read(size, offset)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("mount")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)
    # fuse = FUSE(Memory(), args.mount, foreground=True, allow_other=True)
    fuse = fuse.FUSE(KubernetesFs(), args.mount, foreground=True)

    # print(list(kubeconfig.KubeConfigExplorer().get_all_clusters()))
