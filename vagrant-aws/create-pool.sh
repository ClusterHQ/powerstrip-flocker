#!/usr/bin/env bash

zfs_pool_name="flocker"

if [[ -b /dev/xvdb ]]; then
    echo "Detected EBS environment, setting up real zpool..."
    # There may be a left-over pool from before, but it hasn't got the same
    # data. So destroy it.
    zpool destroy -f $zfs_pool_name
    # Then create it again.
    zpool create $zfs_pool_name /dev/xvdb
elif [[ ! -b /dev/sdb ]]; then
    echo "Setting up a toy zpool..."
    truncate -s 10G /$zfs_pool_name-datafile
    zpool create $zfs_pool_name /$zfs_pool_name-datafile
fi
