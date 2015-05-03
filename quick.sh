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

# This is a docker binary which gets scp'd onto the nodes...
DOCKER_BINARY="${HOME}/Projects/docker/bundles/1.5.0-plugins/binary/docker-1.5.0-plugins"

KEY="${HOME}/.ssh/id_rsa_flocker"
DOCKER_PATH_ON_HOST="/usr/bin/docker"

NODE1="172.16.255.240"
NODE2="172.16.255.241"

for NODE in $NODE1 $NODE2; do
    if [ -e $DOCKER_BINARY ]; then
        echo "Uploading modified docker to test node..."
        scp -i $KEY $DOCKER_BINARY vagrant@$NODE:$DOCKER_PATH_ON_HOST
        ssh -i $KEY vagrant@$NODE systemctl restart docker
        ssh -i $KEY vagrant@$NODE docker --version
    fi
done

if [ "$1" != "--no-build" ]; then
    docker build -t ${DOCKER_PULL_REPO}/flocker-plugin:volume-plugin .
    docker push ${DOCKER_PULL_REPO}/flocker-plugin:volume-plugin
fi

# Run the tests.
export FLOCKER_ACCEPTANCE_NODES="${NODE1}:${NODE2}"
export FLOCKER_ACCEPTANCE_CONTROL_NODE=${NODE1}
export FLOCKER_ACCEPTANCE_AGENT_NODES=${FLOCKER_ACCEPTANCE_NODES}
trial ${2:-powerstripflocker.test.test_acceptance}
