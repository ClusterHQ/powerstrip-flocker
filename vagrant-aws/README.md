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

Create a new file called settings.yml:

```
$ cat <<EOF > settings.yml
ssh_private_key_path: /Users/luke/Downloads/luke.pem
aws_keypair_name: luke
aws_access_key_id: 12345
aws_secret_access_key: abcde
EOF
```

```
$ vagrant up
```

Wait for your nodes to come up, then log into them to run:

```
$ vagrant ssh node1
node1$ docker run -v /flocker/test:/data ubuntu sh -c "cat data > /data/foo"
node1$ exit
$ vagrant ssh node2
node2$ docker run -v /flocker/test:/data ubuntu cat /data/foo
data
node2$
```

