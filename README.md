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

`powerstrip-flocker` connects the [Docker Remote API](https://docs.docker.com/reference/api/docker_remote_api/) to the [new Flocker Volumes API](http://doc-dev.clusterhq.com/advanced/api.html) via [Powerstrip](https://github.com/clusterhq/powerstrip).

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

In other words, `powerstrip-flocker` exposes a *global namespace* (`/flocker/*`) of volumes which flocker will move into place just-in-time before letting docker start your containers.

## Orchestration

Because [powerstrip-flocker](https://github.com/ClusterHQ/powerstrip-flocker) presents a standard docker api - it means that the full gamut of orchestration tools can work with it:

 * [kubernetes](https://github.com/googlecloudplatform/kubernetes)
 * [swarm](https://github.com/docker/swarm/)
 * [mesosphere](https://github.com/mesosphere/marathon)
 * [fleet](https://github.com/coreos/fleet)

These tools don't have the concept of "portable volumes" - by leveraging the [Powerstrip](https://github.com/ClusterHQ/powerstrip) API - [powerstrip-flocker](https://github.com/ClusterHQ/powerstrip-flocker) brings this concept to all of them for free.

## Composition

Equally, [powerstrip-flocker](https://github.com/ClusterHQ/powerstrip-flocker) will work alongside other docker extension projects like networking tools:

 * [weave](https://github.com/zettio/weave)
 * [socketplane](https://github.com/socketplane/socketplane)
 * [calico](https://github.com/Metaswitch/calico)

The above tools "wrap" the docker cli and it was impossible to use them alongside other extensions like [Flocker](https://github.com/ClusterHQ/flocker).
This is because both tools "wrap" the docker cli meaning only one can be used per container.

[Powerstrip](https://github.com/ClusterHQ/powerstrip) allows the composition of multiple adapters.
This means that a single docker host can now implement solutions for two of the critical issues which crop up when you run Docker on multiple hosts in production: storage and networking.

## Is it ready yet?

This is a very early technology preview and has some [big gaps](https://github.com/ClusterHQ/powerstrip-flocker/issues).
What's more, powerstrip itself is a prototype for the new Docker remote API extensions mechanism, and is therefore by definition unstable.

But, you can kick the tyres and try it today!

Then [let us know what you think](https://github.com/ClusterHQ/powerstrip-flocker/issues/new), to encourage us or tell us we're stupid.

## OK, how do I try it?

We've put together a special demo preview environment:

You can try out our demo environment either with vagrant on local files, or on AWS.

### Vagrant

This uses vagrant to bring up the demo on your local machine.

[Click here for the Vagrant demo](https://github.com/ClusterHQ/powerstrip-flocker/tree/master/vagrant)

### AWS

This uses vagrant to bring up the demo on AWS EC2 instances.

[Click here for the AWS demo](https://github.com/ClusterHQ/powerstrip-flocker/tree/master/vagrant-aws)
