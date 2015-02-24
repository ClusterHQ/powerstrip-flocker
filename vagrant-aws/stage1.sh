#!/usr/bin/env bash

export DEBIAN_FRONTEND=noninteractive

apt-get update

echo "Installing ZFS from latest git HEAD"
apt-get -y install build-essential gawk alien fakeroot linux-headers-$(uname -r) zlib1g-dev uuid-dev libblkid-dev libselinux-dev parted lsscsi dh-autoreconf linux-crashdump git

# As of Feb 18 2015, recommended ZoL revisions from Richard Yao:
good_zfs_version="d958324f97f4668a2a6e4a6ce3e5ca09b71b31d9"
good_spl_version="47af4b76ffe72457166e4abfcfe23848ac51811a"
zfs_pool_name="flocker"

# Compile and install spl
cd ~/
git clone https://github.com/zfsonlinux/spl
cd spl
git checkout $good_spl_version
./autogen.sh
./configure
make
make deb
sudo dpkg -i *.deb

# Compile and install zfs
cd ~/
git clone https://github.com/zfsonlinux/zfs
cd zfs
git checkout $good_zfs_version
./autogen.sh
./configure
make
make deb
sudo dpkg -i *.deb

# TODO - reboot!

if [[ -b /dev/xvdb ]]; then
    echo "Detected EBS environment, setting up real zpool..."
    umount /mnt
    zpool create $zfs_pool_name /dev/xvdb
elif [[ ! -b /dev/sdb ]]; then
    echo "Setting up a toy zpool..."
    truncate -s 10G /$zfs_pool_name-datafile
    zpool create $zfs_pool_name /$zfs_pool_name-datafile
fi
