## Quickstart


### Ubuntu


#### System packages

Let's first check the version of your system Python:

```bash
$ python -V
Python 3.8.10
```

Install the fuse packages and the python-venv package matching your installed
version:

```bash
$ sudo apt install fuse libfuse2 python3.8-venv
```


### Project setup (the scripted way)

These scripts automate the manual setup below:

```bash
# kubefs
$ mkdir ~/kubeview
$ ./kfs ~/kubeview

# podview
./pv
```

Both of these scripts assume that you either:
- Don't have a virtual environment in `.ve/` at all (it will setup it up for
  you), or
- You have a fully populated virtual environment in `.ve/`

If you encounter errors when using these scripts it's best to `rm -rf .ve` and
re-run them.


### Project setup (the manual way)

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
(kubefs) $ mkdir ~/kubeview
(kubefs) $ bin/kubefs ~/kubeview

# podview
(kubefs) $ bin/podview
```

