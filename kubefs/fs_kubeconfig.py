from kubefs.fs_model import Directory, File
from kubefs.kubeconfig import Context, User


class KubeConfigClustersDir(Directory):
    @classmethod
    def create(cls, *, name, loader):
        self = cls(name=name)
        self.loader = loader
        return self

    def get_entries(self):
        if not self._lazy_entries:
            clusters = self.loader.get_all_clusters()

            dirs = []
            for cluster in clusters:
                dir = Directory(name=cluster.name)
                dirs.append(dir)

            self._lazy_entries = dirs

        return self._lazy_entries


class KubeConfigContextDir(Directory):
    @classmethod
    def create(cls, *, name, context: Context):
        self = cls(name=name)
        self.context = context
        return self

    def get_entries(self):
        if not self._lazy_entries:
            dirs = []

            cluster = self.context.get_cluster()
            if cluster:
                dir = Directory(name="cluster")
                dirs.append(dir)

            user = self.context.get_user()
            if user:
                dir = KubeConfigUserDir.create(name="user", user=user)
                dirs.append(dir)

            self._lazy_entries = dirs

        return self._lazy_entries


class KubeConfigContextsDir(Directory):
    @classmethod
    def create(cls, *, name, loader):
        self = cls(name=name)
        self.loader = loader
        return self

    def get_entries(self):
        if not self._lazy_entries:
            contexts = self.loader.get_all_contexts()

            dirs = []
            for context in contexts:
                dir = KubeConfigContextDir.create(name=context.name, context=context)
                dirs.append(dir)

            self._lazy_entries = dirs

        return self._lazy_entries


class KubeConfigUserDir(Directory):
    """Represents a directory that contains files that belong to a single user.
    The files and their contents are the key/values of the user object in the
    kube config."""

    @classmethod
    def create(cls, *, name, user: User):
        self = cls(name=name)
        self.user = user
        return self

    def get_entries(self):
        if not self._lazy_entries:
            files = []

            for attname in self.user.get_attribute_names():
                value = self.user.get_attribute(attname)
                if value is not None:
                    file = File(name=attname, contents=value.encode())
                    files.append(file)

            self._lazy_entries = files

        return self._lazy_entries


class KubeConfigUsersDir(Directory):
    """Represents a directory containing all the user names defined in the kube
    config. Each entry is itself a directory containing files."""

    @classmethod
    def create(cls, *, name, loader):
        self = cls(name=name)
        self.loader = loader
        return self

    def get_entries(self):
        if not self._lazy_entries:
            users = self.loader.get_all_users()

            dirs = []
            for user in users:
                dir = KubeConfigUserDir.create(name=user.name, user=user)
                dirs.append(dir)

            self._lazy_entries = dirs

        return self._lazy_entries
