#!/bin/sh
# run this from inside the docker dir
docker run --privileged --rm -e DOCKER_GITCOMMIT=`git log -1 --format=%%h` -v `pwd`:/go/src/github.com/docker/docker custom-docker hack/make.sh binary
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@$1 initctl stop docker
scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -i ~/.ssh/id_rsa_flocker bundles/1.7.0-dev/binary/docker-1.7.0-dev root@$1:/usr/bin/docker
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@$1 initctl start docker
