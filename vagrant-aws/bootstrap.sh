#!/usr/bin/env bash

if [ -x /vagrant ]; then
    cd /vagrant
fi

./stage1.sh
./stage2.sh
#./create-pool.sh
