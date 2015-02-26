# Getting flocker-powerstrip demo working on AWS

Requirements: vagrant, virtualbox, python

Get vagrant-aws:

```
$ vagrant plugins install vagrant-aws
```

Make sure you have checked out this repo and are in the vagrant-aws directory:

```
$ git clone https://github.com/clusterhq/powerstrip-flocker
$ cd powerstrip-flocker/vagrant-aws
```

Copy settings.yml.sample to settings.yml and fill in the details.

```
$ vagrant up --provider=aws
```

Wait for your nodes to come up, then teach them about eachother:

```
$ ./push-config.py
```

This will also set up system services on the nodes.



```
$ vagrant ssh node1
node1$ docker run -v /flocker/test:/data ubuntu sh -c "cat data > /data/foo"
node1$ exit
$ vagrant ssh node2
node2$ docker run -v /flocker/test:/data ubuntu cat /data/foo
data
node2$
```
