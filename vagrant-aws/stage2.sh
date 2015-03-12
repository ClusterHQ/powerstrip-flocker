#!/usr/bin/env bash

#good_flocker_version="edf19adc2b620562f75f5c1e065d253344a5152d"

export DEBIAN_FRONTEND=noninteractive

if [[ ! -x /vagrant ]]; then
    ln -s /root/ubuntu /vagrant
fi

#echo "Cloning flocker..."
#cd /opt
#git clone https://github.com/clusterhq/flocker
#cd flocker
#git checkout $good_flocker_version

#apt-get -y install python-setuptools python-dev

# uhhh.. hack
#cd ~/
#wget https://pypi.python.org/packages/source/m/machinist/machinist-0.2.0.tar.gz
#tar zxfv machinist-0.2.0.tar.gz
#cd machinist-0.2.0
#python setup.py install

# uhhh.. hack
#cd ~/
#wget https://pypi.python.org/packages/source/m/machinist/eliot-0.6.0.tar.gz
#tar zxfv eliot-0.6.0.tar.gz
#cd eliot-0.6.0
#python setup.py install

# now install flocker
#cd /opt/flocker
#python setup.py install

# now install docker
apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 36A1D7869245C8950F966E92D8576A8BA88D21E9

echo deb https://get.docker.io/ubuntu docker main > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get -y install lxc-docker

sed -i'backup' s/USE_KDUMP=0/USE_KDUMP=1/g /etc/default/kdump-tools

apt-get -y install supervisor

docker pull ubuntu:latest
docker pull clusterhq/powerstrip-flocker:latest
docker pull clusterhq/powerstrip:unix-socket
docker pull lmarsden/flocker-control
docker pull lmarsden/flocker-zfs-agent
