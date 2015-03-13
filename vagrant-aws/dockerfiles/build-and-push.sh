#!/bin/bash -xe
cd flocker-control
docker build -t lmarsden/flocker-control .
docker push lmarsden/flocker-control
cd ..
cd flocker-zfs-agent
docker build -t lmarsden/flocker-zfs-agent .
docker push lmarsden/flocker-zfs-agent
cd ..
