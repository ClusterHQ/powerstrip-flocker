#!/usr/bin/env bash

good_flocker_version="ff051f09f22a5e9ce950e86dd2a82bb23406b888"

export DEBIAN_FRONTEND=noninteractive

if [[ ! -x /vagrant ]]; then
    ln -s /root/ubuntu /vagrant
fi

zfs create hpool/hcfs
zfs set mountpoint=/hcfs hpool/hcfs

echo "Cloning flocker..."
cd /opt
git clone https://github.com/clusterhq/flocker
cd flocker
git checkout $good_flocker_version
python setup.py install

# Use pip to upgrade itself and install all requirements
#pip install --upgrade pip
#easy_install -U distribute # An error message told me to do this :(
# at this point, /usr/bin/pip has been replaced by /usr/local/bin/pip :(
#/usr/local/bin/pip install -r requirements.txt

# Link in our supervisord config
#ln -s /opt/flocker.../supervisor/flocker /etc/supervisor/conf.d/...

# TODO - restart supervisord automatically after putting cluster config in place

apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 36A1D7869245C8950F966E92D8576A8BA88D21E9

echo deb https://get.docker.io/ubuntu docker main > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get -y install lxc-docker

sed -i'backup' s/USE_KDUMP=0/USE_KDUMP=1/g /etc/default/kdump-tools
