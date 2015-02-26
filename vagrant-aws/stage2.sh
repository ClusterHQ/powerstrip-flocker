#!/usr/bin/env bash

good_flocker_version="bcc7bb4280629a67b97da7750ca6e513767aad21"

export DEBIAN_FRONTEND=noninteractive

if [[ ! -x /vagrant ]]; then
    ln -s /root/ubuntu /vagrant
fi

echo "Cloning flocker..."
cd /opt
git clone https://github.com/clusterhq/flocker
cd flocker
git checkout $good_flocker_version

apt-get -y install python-setuptools python-dev

# uhhh.. hack
cd ~/
wget https://pypi.python.org/packages/source/m/machinist/machinist-0.2.0.tar.gz
tar zxfv machinist-0.2.0.tar.gz
cd machinist-0.2.0
python setup.py install

# now install flocker
cd /opt/flocker
python setup.py install

# now install docker
apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 36A1D7869245C8950F966E92D8576A8BA88D21E9

echo deb https://get.docker.io/ubuntu docker main > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get -y install lxc-docker

apt-get -y install supervisor

sed -i'backup' s/USE_KDUMP=0/USE_KDUMP=1/g /etc/default/kdump-tools
