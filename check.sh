#!/bin/sh

for dir in akube bin kube kubefs podview; do
    isort $dir
    black $dir
    mypy $dir
done
