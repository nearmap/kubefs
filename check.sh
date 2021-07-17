#!/bin/sh

for dir in bin kube kubefs podview; do
    isort $dir
    black $dir
    mypy $dir
done
