# Building the AMIs referenced in this demo

This documents the process of building the AMI referenced in this demo.

It's in two parts - compiling zfs and installing flocker, so that if we want to upgrade the demo to a newer version of flocker we don't have to wait for zfs to build again.

If you are just trying out powerstrip-flocker, you can ignore these instructions.
See README.md in this directory instead.

# stage 1 - compiling zfs

* Edit Vagrantfile and comment out all the `aws.ami` lines apart from `aws.ami = "ami-3cf8b154" # ubuntu 14.04`.
  This is the ubuntu 14.04 base AMI.
* Edit bootstrap.sh and uncomment `./stage1.sh` and comment out `stage2.sh`.
* Run `vagrant up` and wait for ZFS to compile.
* Log into node1 with `vagrant ssh node1` and run `sudo mv ~/.ssh/authorized_keys ~/.ssh/authorized_keys.disabled`
* Log into the AWS console and create an AMI from the current running state of node1
* Now you can put back the changes you made to `Vagrantfile` and `bootstrap.sh`, and put the new AMI ID into the Vagrantfile.

# stage 2 - installing flocker

* ...
