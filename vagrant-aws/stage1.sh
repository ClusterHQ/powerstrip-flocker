#!/usr/bin/env bash

export DEBIAN_FRONTEND=noninteractive

apt-get update

echo "Installing ZFS from latest git HEAD"
apt-get -y install build-essential gawk alien fakeroot linux-headers-$(uname -r) zlib1g-dev uuid-dev libblkid-dev libselinux-dev parted lsscsi dh-autoreconf linux-crashdump git

# As of Apr 2 2015, recommended ZoL revisions from Richard Yao:
good_zfs_version="7f3e466"
good_spl_version="6ab0866"

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

