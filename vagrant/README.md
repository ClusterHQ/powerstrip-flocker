# powerstrip-flocker demo on Vagrant 

This demo will guide you through the steps needed to run the multi-node powerstrip-flocker demo using Vagrant.

## Requirements

Ensure that you have the following installed on your system:

 * [virtualbox](https://www.virtualbox.org/wiki/Downloads)
 * [vagrant](http://www.vagrantup.com/downloads.html)


## Setup

#### Clone repository

Make sure you have checked out this repo and are in the vagrant-aws directory:

```bash
$ git clone https://github.com/clusterhq/powerstrip-flocker
$ cd powerstrip-flocker/vagrant
```

#### `vagrant up`

Now we type `vagrant up` which will spin up the two nodes.

```bash
$ vagrant up
```

## Demo

Now we have the 2 machines - we can use flocker to migrate our data!

On the first node we write some data to a flocker volume using nothing but the standard docker client.

```bash
$ vagrant ssh node1
node1$ sudo docker run -v /flocker/test:/data ubuntu sh -c "echo data > /data/foo"
node1$ exit
```

On the second node we trigger a migration of that data and read it - using nothing but the standard docker client!

```bash
$ vagrant ssh node2
node2$ sudo docker run -v /flocker/test:/data ubuntu cat /data/foo
data
node2$ exit
```

## Explanation

What just happened was the following:

 * the `docker run` command on node1 was intercepted by powerstrip
 * powerstrip sent the volume information to powerstrip-flocker
 * powerstrip-flocker created the volume with flocker
 * the container started and wrote some data to the volume
 * the `docker run` command on node2 was sent to powerstrip-flocker
 * it noticed that this volume had already been created on node1
 * flocker then moved the volume over the node2
 * the data that was written to node1 was read from node2

## caveat

Warning: do not use this for anything!
As well as being as a massive hack, this demo uses ephemeral instance storage for the ZFS pool.
So you *will* lose your data.
