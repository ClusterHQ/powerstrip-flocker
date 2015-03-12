#!/usr/bin/env bash

zfs_pool_name="flocker"

if [[ -b /dev/xvdb ]]; then
    echo "Detected EBS environment, setting up real zpool..."
    umount /mnt # this is where xvdb is mounted by default
    zpool create $zfs_pool_name /dev/xvdb
elif [[ ! -b /dev/sdb ]]; then
    echo "Setting up a toy zpool..."
    truncate -s 10G /$zfs_pool_name-datafile
    zpool create $zfs_pool_name /$zfs_pool_name-datafile
fi

# create and destroy a dataset to exercise zfs automount
zfs create flocker/ignored
zfs set mountpoint=/flocker/ignored flocker/ignored
zfs destroy flocker/ignored
