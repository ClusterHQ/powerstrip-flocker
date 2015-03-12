#!/bin/bash -xe
cd flocker-control
sudo docker build -t lmarsden/flocker-control .
sudo docker push lmarsden/flocker-control
cd ..
cd flocker-zfs-agent
sudo docker build -t lmarsden/flocker-zfs-agent .
sudo docker push lmarsden/flocker-zfs-agent
cd ..
