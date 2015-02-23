## powerstrip-flocker: portable volumes using just the docker cli
*or: how I learned to love running stateful docker containers and stop worrying where the data is*

![flying books to illustrate portable volumes](resources/flying_books.jpg)

(Portable "volumes", hee hee.)

## What's the problem?

When you want to run Docker in production, you want to run it across multiple machines and you probably want to use some orchestration tools.
However, when you attach a volume to a Docker container, the machine it's running on becomes [a pet when it should be cattle](http://www.theregister.co.uk/2013/03/18/servers_pets_or_cattle_cern/).

## The solution

You should be able to run a stateful container with a given volume on any host in your cluster, and the platform should handle moving data around as necessary.

## What is `powerstrip-flocker`?

`powerstrip-flocker` allows you to use the regular `docker` CLI commands to create or move flocker volumes, automatically moving volumes around between hosts in the cluster as-needed.

## How does it work?

`powerstrip-flocker` connects the [Docker Remote API](https://docs.docker.com/reference/api/docker_remote_api/) to the [new Flocker Volumes API](doc-dev.clusterhq.com/advanced/api.html) via [Powerstrip](https://github.com/clusterhq/powerstrip).

## Killer demo

Write some data into a volume on one host, read it from another:

```
$ ssh node1 docker run -v /flocker/demo:/data busybox sh -c "echo fish > /data/file"
$ ssh node2 docker run -v /flocker/demo:/data busybox sh -c "cat /data/file"
fish
```

Note that the volume above has become "global" to both hosts.

## What this means

Finally you can run stateful containers in docker and stop worrying about where the data is.

In other words, `powerstrip-flocker` exposes a *global volume namespace* (`/flocker/*`).

### Works with orchestration

Because powerstrip speaks the Docker API, you can use powerstrip-flocker with your docker tools of choice, be it the plain ole' `docker` CLI, `swarm`, `mesosphere`, `kubernetes`, `fleet` or anything else that speaks the [Docker remote API](https://docs.docker.com/reference/api/docker_remote_api/).

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
