import os
import re
import stat
import time

from kubefs import system


class RootFsProvider:
    # all my entries are directories
    entries = [
        'clusters',
        'contexts',
        'users',
    ]

    def get_entry_names(self):
        return self.entries

    def get_attributes(self, entry):
        return system.get_default_dir_atts()

