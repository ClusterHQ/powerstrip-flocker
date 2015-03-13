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

# create a dataset to exercise zfs automount and leave it open
zfs create flocker/ignored
zfs set readonly=off flocker
