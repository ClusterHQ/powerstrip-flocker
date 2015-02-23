## powerstrip-flocker: portable volumes using just the docker cli
*or: how I learned to love running stateful containers in docker and stop worrying where the data is*

![flying books to illustrate portable volumes](resources/flying_books.jpg)
(Portable "volumes", hee hee.)

## What is `powerstrip-flocker`?

`powerstrip-flocker` is a way of configuring docker which lets you use regular docker CLI commands or orchestration frameworks to create or move flocker volumes around between hosts in a cluster.

## How does it work?

`powerstrip-flocker` muxes between the [Docker Remote API](https://docs.docker.com/reference/api/docker_remote_api/) via [Powerstrip](https://github.com/clusterhq/powerstrip) and the [new Flocker Volumes API](doc-dev.clusterhq.com/advanced/api.html).

## Killer demo

Write some data into a volume on one host, read it from another:

```
$ ssh node1 docker run -v /flocker/demo:/data busybox sh -c "echo fish > /data/file"
$ ssh node2 docker run -v /flocker/demo:/data busybox sh -c "cat /data/file"
fish
```

## What this means

Finally you can run stateful containers in docker and stop worrying about where the data is.

### Works with orchestration

Because powerstrip speaks the Docker API, you can use powerstrip-flocker with your docker tools of choice, be it the plain ole' `docker` CLI, `swarm`, `mesosphere`, `kubernetes`, or anything else that speaks the [Docker remote API](https://docs.docker.com/reference/api/docker_remote_api/).

### Works with other prototypical extensions, e.g. networking

Because powerstrip can compose prototypical docker extensions, you can use (compose) `powerstrip-flocker` nicely along with `powerstrip-weave`, `socketplane`, or [any other `powerstrip` adapter that exists](https://github.com/clusterhq/powerstrip#powerstrip-adapters).

## Is it ready yet?

This is a very early technology preview and has some [big gaps](https://github.com/ClusterHQ/powerstrip-flocker/issues).
What's more, powerstrip itself is a prototype for the new Docker remote API extensions mechanism, and is therefore by definition unstable.

But, you can kick the tyres and try it today!

Then [let us know what you think](https://github.com/ClusterHQ/powerstrip-flocker/issues/new), to encourage us or tell us we're stupid.

## OK, how do I try it?

Run the following commands on your OS X or Linux host with Vagrant and Virtualbox installed, and you can try out our :

```
# ...
```
