# Building the AMIs referenced in this demo

This documents the process of building the AMI referenced in this demo.

It's in two parts - compiling zfs and installing flocker, so that if we want to upgrade the demo to a newer version of flocker we don't have to wait for zfs to build again.

If you are just trying out powerstrip-flocker, you can ignore these instructions.
See README.md in this directory instead.

# stage 1 - compiling zfs

* Edit Vagrantfile and comment out all the `aws.ami` lines apart from `aws.ami = "ami-3cf8b154" # ubuntu 14.04`.
  This is the ubuntu 14.04 base AMI.
* Edit bootstrap.sh and make it only run `./stage1.sh`.
* Run `vagrant up` and wait for ZFS to compile.
* Follow "making a new AMI" steps

# stage 2 - installing flocker

* Make bootstrap.sh run only `./stage2.sh`.
* Follow "making a new AMI" steps


# making a new AMI

* Log into node1 with `vagrant ssh node1` and run `sudo mv ~/.ssh/authorized_keys ~/.ssh/authorized_keys.disabled`.
* `rm /vagrant/{settings.yml,access_key_id.txt,secret_access_key.txt}` (ideally this would be a secure destroy, or not have this file copied in in the first place)
* Log into the AWS console and create an AMI from the current running state of node1 (named "flocker-powerstrip master").
* Now you can revert any changes you made to `Vagrantfile` and `bootstrap.sh`, and put the new AMI ID into the Vagrantfile.


# at vagrant provisioning time

* Need to create the zpool.
