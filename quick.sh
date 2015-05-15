#!/usr/bin/env bash
set -x -e

# First run (do this manually):
# $ vagrant box add \
#       http://build.clusterhq.com/results/vagrant/master/flocker-tutorial.json
# $ admin/run-powerstrip-acceptance-tests \
#       --keep --distribution=fedora-20 powerstripflocker.test.test_acceptance
# This will set up some VMs, which will take a while.

# Then you can run the following to do fast development cycles (replace
# 'lmarsden' or 'clusterhq' with your own repo here and in test_acceptance.py
# if necessary):

# Run ./quick.sh --no-build to make it even quicker (if you've only changed the
# acceptance test and not the actual adapter).

# This should match up with DOCKER_PULL_REPO in powerstripflocker/test/test_acceptance.py
DOCKER_PULL_REPO="lmarsden"
PF_VERSION="new_integration_tests"

# This is a docker binary which gets scp'd onto the nodes...

# Recipe to create this binary on the host:
# $ export BRANCHNAME=some_docker_branch
# $ mkdir -p ~/Projects; cd ~/Projects
# $ if [ ! -e docker ]; then git clone git@github.com:clusterhq/docker-plugins; mv docker-plugins docker; fi
# $ cd docker
# $ git checkout $BRANCHNAME
# $ docker build -t $BRANCHNAME .
# $ docker run --privileged --rm -ti -v `pwd`:/go/src/github.com/docker/docker $BRANCHNAME hack/make.sh binary

DOCKER_BINARY="${PWD}/docker/bundles/1.7.0-dev/binary/docker-1.7.0-dev"

KEY="${HOME}/.ssh/id_rsa_flocker"
DOCKER_PATH_ON_HOST="/usr/bin/docker"
USER="root"

NODE1="172.16.255.240"
NODE2="172.16.255.241"

for NODE in $NODE1 $NODE2; do
    if [ -e $DOCKER_BINARY ]; then
        echo "Uploading modified docker to test node..."
        ssh -i $KEY $USER@$NODE initctl stop docker
        scp -i $KEY $DOCKER_BINARY $USER@$NODE:$DOCKER_PATH_ON_HOST
        ssh -i $KEY $USER@$NODE initctl start docker
        ssh -i $KEY $USER@$NODE docker --version
    fi
done

if [ "$1" != "--no-build" ]; then
    docker build -t ${DOCKER_PULL_REPO}/flocker-plugin:${PF_VERSION} .
    docker push ${DOCKER_PULL_REPO}/flocker-plugin:${PF_VERSION}
fi

# Run the tests.
export FLOCKER_ACCEPTANCE_NODES="${NODE1}:${NODE2}"
export FLOCKER_ACCEPTANCE_CONTROL_NODE=${NODE1}
export FLOCKER_ACCEPTANCE_AGENT_NODES=${FLOCKER_ACCEPTANCE_NODES}
trial ${2:-powerstripflocker.test.test_acceptance}

