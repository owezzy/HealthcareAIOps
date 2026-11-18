#!/bin/sh
# cgroup v2 preparation for a K3s node running inside a container (ADR-0013).
#
# In a private cgroup namespace the container's processes sit in the
# namespace root cgroup. cgroup v2 forbids enabling controllers for children
# of a cgroup that still holds processes, so the kubelet cannot create pod
# cgroups. The same technique as Docker-in-Docker and k3d: move every
# process into a child cgroup, then delegate all controllers to children.
set -eu

if [ -f /sys/fs/cgroup/cgroup.controllers ]; then
    mkdir -p /sys/fs/cgroup/init
    # Moving can race with exiting processes; anything left is moved by the retry.
    for attempt in 1 2 3; do
        for pid in $(cat /sys/fs/cgroup/cgroup.procs); do
            echo "$pid" > /sys/fs/cgroup/init/cgroup.procs 2>/dev/null || true
        done
        [ -z "$(cat /sys/fs/cgroup/cgroup.procs)" ] && break
    done
    for controller in $(cat /sys/fs/cgroup/cgroup.controllers); do
        echo "+$controller" > /sys/fs/cgroup/cgroup.subtree_control
    done
fi

exec /bin/k3s "$@"
