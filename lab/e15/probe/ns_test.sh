#!/bin/bash
# usage: ns_test.sh RUNDIR
RUNDIR=$1
mount -t tmpfs tmpfs /home/claude
mkdir -p $RUNDIR /home/claude/.claude/remote
mount --bind /proc/self/root/$RUNDIR $RUNDIR 2>/dev/null || true
