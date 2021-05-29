# A fuse filesystem for browsing Kubernetes clusters

`kubefs` is a read-only filesystem that runs in user space (don't need to be
`root` to mount it) that allows you to browse objects in your Kubernetes
clusters.

It loads your kube config(s) from `$KUBECONFIG` or `~/.kube` and uses that to
present a top level view for you to navigate:

```bash
$ ls -p ~/kubeview
clusters/  contexts/  users/
```

You can use this to explore the cluster:

```bash
$ ls -p ~/kubeview/clusters
minikube/

$ ls -p ~/kubeview/clusters/minikube
configmaps/  deployments/  endpoints/  namespaces/  nodes/  pods/  replicasets/  secrets/  services/

$ ls -p ~/kubeview/clusters/minikube/pods
coredns-74ff55c5b-xd6nf  etcd-minikube  kube-apiserver-minikube  kube-controller-manager-minikube  kube-proxy-66s6j  kube-scheduler-minikube  storage-provisioner

$ head ~/kubeview/clusters/minikube/pods/etcd-minikube
{
    "api_version": "v1",
    "kind": "Pod",
    "metadata": {
        "annotations": {
...
```


## Quickstart

Installing:

```bash
$ mkvirtualenv kubefs

(kubefs) $ pip install -r requirements.txt
```

Mounting the filesystem:

```bash
# create a mount point
(kubefs) $ mkdir ~/kubeview

# mount the filesystem there
(kubefs) $ python -m kubefs.main ~/kubeview
```