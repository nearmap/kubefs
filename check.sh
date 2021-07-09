#!/bin/sh

for dir in bin kube kubefs; do
	isort $dir
	black $dir
done
