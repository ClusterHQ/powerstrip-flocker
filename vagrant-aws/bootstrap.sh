#!/usr/bin/env bash

if [ -x /vagrant ]; then
    cd /vagrant
fi

#./stage1.sh
#./stage2.sh

zfs_pool_name="flocker"

if [[ -b /dev/xvdb ]]; then
    echo "Detected EBS environment, setting up real zpool..."
    umount /mnt
    zpool create $zfs_pool_name /dev/xvdb
elif [[ ! -b /dev/sdb ]]; then
    echo "Setting up a toy zpool..."
    truncate -s 10G /$zfs_pool_name-datafile
    zpool create $zfs_pool_name /$zfs_pool_name-datafile
fi
