## Getting started

Requirements:
​
* Python 3.8 or later.
* Additional dependencies for `kubefs` (not required for `podview`):
  * `fuse` (available on Linux and [Mac](https://osxfuse.github.io/))


### Ubuntu


#### System packages

Let's first check the version of your system Python:

```bash
$ python3 -V
Python 3.8.10
```

Install the fuse packages and the python-venv package matching your installed
version:

```bash
$ sudo apt install fuse libfuse2 python3.8-venv
```


### Project setup (the scripted way)

Clone the repository:

```bash
$ git clone https://github.com/nearmap/kubefs
$ cd kubefs
```

These scripts automate the manual setup below:

```bash
# kubefs
$ mkdir -p ~/kubeview
$ ./kfs ~/kubeview

# podview
$ ./pv
```

They basically manage the virtual environment for you, so they *have to be run
outside of the virtual environment*.

The scripts assume that you either:
- Don't have a virtual environment in `.ve/` at all (it will setup it up for
  you), or
- You have a fully populated virtual environment in `.ve/`


### Project setup (the manual way)

Clone the repository:

```bash
$ git clone https://github.com/nearmap/kubefs
$ cd kubefs
```

If you are using `virtualenvwrapper` create the virtual environment - this will
also activate it:

```bash
$ mkvirtualenv --python $(which python3) kubefs
(kubefs) $
```

When you come back to the project later on re-activate it by doing:

```bash
$ workon kubefs
(kubefs) $
```

If you prefer not to use `virtualenvwrapper` create the virtual environment by
doing:

```bash
$ python3 -m venv .ve
```

Activate it by doing:

```bash
$ . .ve/bin/activate
(kubefs) $
```

Once you've activated the virtual environment install the dependencies into it:

```bash
(kubefs) $ pip install -r requirements.txt
```

Finally, make sure kubefs and podview can be started without errors:

```bash
# kubefs
(kubefs) $ mkdir -p ~/kubeview
(kubefs) $ bin/kubefs ~/kubeview

# podview
(kubefs) $ bin/podview
```


### Troubleshooting

**While creating/installing dependencies into a virtual environment I see
errors in red, something about `Failed building wheel`.**

These are not fatal errors and you can ignore them.

**When running `kubefs` or `podview` I get `FileNotFoundError: [Error 2] No such
file or directory: '/home/user/.kube'`.**

Your kube config files could not be detected.

If you have `$KUBECONFIG` set make sure it's pointing at one or more valid kube
config files, eg. `KUBECONFIG=~/.kube/cluster1;~/.kube/cluster2`.

Otherwise, make sure that your `~/.kube` directory contains at least one valid
kube config file.



If you encounter errors when using these scripts it's best to `rm -rf
.ve` and re-run them.