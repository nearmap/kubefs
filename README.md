# A fuse filesystem for browsing Kubernetes clusters

`kubefs` is a read-only filesystem that runs in user space (don't need to be
`root` to mount it) that allows you to browse objects in your Kubernetes
clusters.

It loads your kube config(s) from `$KUBECONFIG` or `~/.kube` and uses that to
present a top level view for you to navigate:

```bash
$ ls -p ~/kubeview
clusters/
contexts/
users/
```

You can use this to explore the cluster:

```bash
$ ls -p ~/kubeview/clusters
minikube/

$ ls -p ~/kubeview/clusters/minikube
configmaps/
deployments/
endpoints/
namespaces/
nodes/
pods/
replicasets/
secrets/
services/

$ ls -p ~/kubeview/clusters/minikube/pods
coredns-74ff55c5b-xd6nf
etcd-minikube
kube-apiserver-minikube
kube-controller-manager-minikube
kube-proxy-66s6j
kube-scheduler-minikube
storage-provisioner

$ head ~/kubeview/clusters/minikube/pods/etcd-minikube
{
    "api_version": "v1",
    "kind": "Pod",
    "metadata": {
        "annotations": {
...
```

Behind the scenes, `kubefs` makes requests to the k8s API server to fetch all
these objects and populate the filesystem. This can be slow, so directory
entries are cached for 60 seconds.


## Quickstart

`kubefs` requires a few libraries to run. The script `kfs` sets all this up on
the first run, so that's all you need. `kubefs` runs in the foreground, so once
you launch it it mounts the filesystem and keeps running until you stop it.
When you stop it, the filesystem is umounted.

Mounting the filesystem:

```bash
# create a mount point
$ mkdir ~/kubeview

# mount the filesystem there
$ ./kfs ~/kubeview
Re-using existing virtualenv at: .ve/ and assuming it's up to date.
If you see errors try 'rm -rf .ve/' and re-run this script.
DEBUG:fuse.log-mixin:-> init / ()
DEBUG:fuse.log-mixin:<- init None
```
