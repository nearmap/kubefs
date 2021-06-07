#!/usr/bin/env python

from kubefs.fs_model import Directory, Payload
from kubefs.fs_kubeconfig import (
    KubeConfigUsersDir,
    KubeConfigClustersDir,
    KubeConfigContextsDir,
)
from kubefs.kubeconfig import KubeConfigLoader
import logging
import os
import errno

import fuse


class KubernetesFs(fuse.LoggingMixIn, fuse.Operations):
    constant_entries = [
        ".",
        "..",
    ]

    def __init__(self):
        self.basepath = os.sep

        loader = KubeConfigLoader.get_instance()
        self.tree = Directory(
            payload=Payload(name=""),
            entries=[
                KubeConfigClustersDir.create(
                    payload=Payload(name="clusters"), loader=loader
                ),
                KubeConfigContextsDir.create(
                    payload=Payload(name="contexts"), loader=loader
                ),
                KubeConfigUsersDir.create(payload=Payload(name="users"), loader=loader),
            ],
        )

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

    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(name)s %(message)s)')
    fuse = fuse.FUSE(KubernetesFs(), args.mount, foreground=True)
