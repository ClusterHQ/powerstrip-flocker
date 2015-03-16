#!/bin/bash

export FLOCKER_CONTROL_PORT=${FLOCKER_CONTROL_PORT:=80}
export FLOCKER_AGENT_PORT=${FLOCKER_AGENT_PORT:=4524}

# supported distributions: "ubuntu", "redhat" (means centos/fedora)
export DISTRO=${DISTRO:="ubuntu"}

export FLOCKER_ZFS_AGENT=flocker-zfs-agent
export FLOCKER_CONTROL=flocker-control
export DOCKER=`which docker`
export BASH=`which bash`

# on subsequent vagrant ups - vagrant has not mounted /vagrant/install.sh
# so we copy it into place
cmd-copy-vagrant-dir() {
  cp -r /vagrant /srv/vagrant
}

# extract the current zfs-agent uuid from the volume.json - sed sed sed!
cmd-get-flocker-uuid() {
  if [[ ! -f /etc/flocker/volume.json ]]; then
    >&2 echo "/etc/flocker/volume.json NOT FOUND";
    exit 1;
  fi
  # XXX should use actual json parser!
  cat /etc/flocker/volume.json | sed 's/.*"uuid": "//' | sed 's/"}//'
}

# wait until the named file exists
cmd-wait-for-file() {
  while [[ ! -f $1 ]]
  do
    echo "wait for file $1" && sleep 1
  done
}

# configure docker to listen on a different unix socket and make sure selinux is not turned on
cmd-configure-docker() {
  if [[ "$DISTRO" == "redhat" ]]; then
    /usr/sbin/setenforce 0
  fi

  echo "configuring docker to listen on unix:///var/run/docker.real.sock";

  if [[ "$DISTRO" == "redhat" ]]; then
    # docker itself listens on docker.real.sock and powerstrip listens on docker.sock
    cat << EOF > /etc/sysconfig/docker-network
DOCKER_NETWORK_OPTIONS=-H unix:///var/run/docker.real.sock --dns 8.8.8.8 --dns 8.8.4.4
EOF

    # the key here is removing the selinux=yes option from docker
    cat << EOF > /etc/sysconfig/docker
OPTIONS=''
DOCKER_CERT_PATH=/etc/docker
TMPDIR=/var/tmp
EOF
  fi

  if [[ "$DISTRO" == "ubuntu" ]]; then
    export DEBIAN_FRONTEND=noninteractive
    apt-get -y install linux-image-extra-$(uname -r) # for aufs
    cat << EOF > /etc/default/docker
# Use DOCKER_OPTS to modify the daemon startup options.
DOCKER_OPTS="-H unix:///var/run/docker.real.sock --dns 8.8.8.8 --dns 8.8.4.4 -s aufs"
EOF
  fi
  cmd-restart-docker
  rm -rf /var/run/docker.sock
}

cmd-enable-system-service() {
  if [[ "$DISTRO" == "redhat" ]]; then
    # create a link for the named systemd unit so it starts at boot
    ln -sf /etc/systemd/system/$1.service /etc/systemd/system/multi-user.target.wants/$1.service
  fi
  if [[ "$DISTRO" == "ubuntu" ]]; then
    # re-read the config files on disk (supervisorctl always has everything enabled)
    supervisorctl update
  fi
}

cmd-reload-process-supervisor() {
  if [[ "$DISTRO" == "ubuntu" ]]; then
    supervisorctl update
  fi
  if [[ "$DISTRO" == "redhat" ]]; then
    systemctl daemon-reload
  fi
}

cmd-start-system-service() {
  if [[ "$DISTRO" == "ubuntu" ]]; then
    supervisorctl start $1
  fi
  if [[ "$DISTRO" == "redhat" ]]; then
    # systemd requires services to be enabled before they're started, but
    # supervisor enables services by default (?)
    systemctl enable $1.service
    systemctl start $1.service
  fi
}

cmd-stop-system-service() {
  if [[ "$DISTRO" == "ubuntu" ]]; then
    supervisorctl stop $1
  fi
  if [[ "$DISTRO" == "redhat" ]]; then
    systemctl stop $1.service
  fi
}

cmd-restart-docker() {
  if [[ "$DISTRO" == "ubuntu" ]]; then
    service docker restart
  fi
  if [[ "$DISTRO" == "redhat" ]]; then
    systemctl restart docker.service
  fi
}

# stop and remove a named container
cmd-docker-remove() {
  echo "remove container $1";
  DOCKER_HOST="unix:///var/run/docker.real.sock" $DOCKER stop $1 2>/dev/null || true
  DOCKER_HOST="unix:///var/run/docker.real.sock" $DOCKER rm $1 2>/dev/null || true
}

# docker pull a named container - this always runs before the docker socket
# gets reconfigured
cmd-docker-pull() {
  echo "pull image $1";
  DOCKER_HOST="unix:///var/run/docker.real.sock" $DOCKER pull $1
}

# configure powerstrip-flocker adapter
cmd-configure-adapter() {
  cmd-fetch-config-from-disk-if-present $@
  local cmd="/srv/vagrant/install.sh start-adapter $IP $CONTROLIP"
  local service="powerstrip-flocker"

  echo "configure powerstrip adapter - $1 $2";

  if [[ "$DISTRO" == "redhat" ]]; then
    cat << EOF > /etc/systemd/system/$service.service
[Unit]
Description=Powerstrip Flocker Adapter
After=docker.service
Requires=docker.service

[Service]
ExecStart=$BASH $cmd
ExecStop=$BASH /srv/vagrant/install.sh docker-remove $service

[Install]
WantedBy=multi-user.target
EOF
  fi
  if [[ "$DISTRO" == "ubuntu" ]]; then
    cat << EOF > /etc/supervisor/conf.d/$service.conf
[program:$service]
command=$BASH $cmd
EOF
  # XXX there's no equivalent "ExecStop" command in supervisor...
  fi

  cmd-enable-system-service $service
}

# the actual boot command for the powerstrip adapter
# we run without -d so that process manager can manage the process properly
cmd-start-adapter() {
  cmd-fetch-config-from-disk-if-present $@
  cmd-docker-remove powerstrip-flocker
  local HOSTID=$(cmd-get-flocker-uuid)
  DOCKER_HOST="unix:///var/run/docker.real.sock" \
  docker run --rm --name powerstrip-flocker \
    --expose 80 \
    -e "MY_NETWORK_IDENTITY=$IP" \
    -e "FLOCKER_CONTROL_SERVICE_BASE_URL=http://$CONTROLIP:80/v1" \
    -e "MY_HOST_UUID=$HOSTID" \
    clusterhq/powerstrip-flocker:latest
}

cmd-configure-powerstrip() {
  local cmd="/srv/vagrant/install.sh start-powerstrip"
  local service="powerstrip"

  echo "configure $service";

  if [[ "$DISTRO" == "redhat" ]]; then
    cat << EOF > /etc/systemd/system/$service.service
[Unit]
Description=Powerstrip Server
After=powerstrip-flocker.service
Requires=powerstrip-flocker.service

[Service]
ExecStart=$BASH $cmd
ExecStop=$BASH /srv/vagrant/install.sh docker-remove $service

[Install]
WantedBy=multi-user.target
EOF
  fi
  if [[ "$DISTRO" == "ubuntu" ]]; then
    cat << EOF > /etc/supervisor/conf.d/$service.conf
[program:$service]
command=$BASH $cmd
EOF
  fi

  cmd-enable-system-service $service
}

# the boot step for the powerstrip container - start without -d so process
# manager can manage the process
cmd-start-powerstrip() {
  rm -rf /var/run/docker.sock
  cmd-docker-remove powerstrip
  DOCKER_HOST="unix:///var/run/docker.real.sock" \
  docker run --rm --name powerstrip \
    -v /var/run:/host-var-run \
    -v /etc/powerstrip-demo/adapters.yml:/etc/powerstrip/adapters.yml \
    --link powerstrip-flocker:flocker \
    clusterhq/powerstrip:unix-socket
  # XXX sleep 5 should be replaced by wait-for-file
  sleep 5
  # XXX should use user defined in settings.yml here; what follows is a
  # presumptuious hack.
  if [[ "$DISTRO" == "redhat" ]]; then
      chgrp vagrant /var/run/docker.sock
  fi
  if [[ "$DISTRO" == "ubuntu" ]]; then
      chgrp docker /var/run/docker.sock
  fi
}

# write out adapters.yml for powerstrip
cmd-powerstrip-config() {
  echo "write /etc/powerstrip-demo/adapters.yml";
  mkdir -p /etc/powerstrip-demo
  cat << EOF >> /etc/powerstrip-demo/adapters.yml
version: 1
endpoints:
  "POST /*/containers/create":
    pre: [flocker]
adapters:
  flocker: http://flocker/flocker-adapter
EOF
}

# write systemd unit file for the zfs agent
cmd-flocker-zfs-agent() {
  local cmd="$BASH /srv/vagrant/install.sh block-start-flocker-zfs-agent $@"
  local service="flocker-zfs-agent"

  echo "configure $service";
  if [[ "$DISTRO" == "redhat" ]]; then
    cat << EOF > /etc/systemd/system/$service.service
[Unit]
Description=Flocker ZFS Agent

[Service]
TimeoutStartSec=0
ExecStart=$cmd

[Install]
WantedBy=multi-user.target
EOF
  fi
  if [[ "$DISTRO" == "ubuntu" ]]; then
    cat << EOF > /etc/supervisor/conf.d/$service.conf
[program:$service]
command=$cmd
EOF
  fi

  cmd-enable-system-service flocker-zfs-agent
}

# runner for the zfs agent
# we wait for there to be a docker socket by waiting for docker info
# we then wait for there to be a powerstrip container
cmd-block-start-flocker-zfs-agent() {
  # we're called from the outside, so figure out network identity etc
  cmd-fetch-config-from-disk-if-present $@
  echo "waiting for docker socket before starting flocker-zfs-agent";
  export DOCKER_HOST="unix:///var/run/docker.real.sock"
  while ! (docker info \
        && sleep 1 && docker info && sleep 1 && docker info \
        && sleep 1 && docker info && sleep 1 && docker info \
        && sleep 1 && docker info); do echo "waiting for /var/run/docker.sock"; sleep 1; done;
  # TODO maaaaybe check for powerstrip container running here?
  mkdir -p /etc/flocker
  docker rm -f flocker-zfs-agent
  docker run --rm --name flocker-zfs-agent \
      -v /etc/flocker:/etc/flocker \
      -v /var/run/docker.real.sock:/var/run/docker.sock \
      -v /root/.ssh:/root/.ssh \
      lmarsden/flocker-zfs-agent $FLOCKER_ZFS_AGENT $IP $CONTROLIP
}


# configure control service with process manager
cmd-flocker-control() {
  local env="DOCKER_HOST=unix:///var/run/docker.real.sock"
  local cmd="docker rm -f flocker-control; docker run --rm --name flocker-control \
            -p $FLOCKER_CONTROL_PORT:$FLOCKER_CONTROL_PORT \
            -p $FLOCKER_AGENT_PORT:$FLOCKER_AGENT_PORT \
            lmarsden/flocker-control \
            $FLOCKER_CONTROL -p $FLOCKER_CONTROL_PORT"
  local service="flocker-control"

  echo "configure $service"

  if [[ "$DISTRO" == "redhat" ]]; then
    cat << EOF > /etc/systemd/system/$service.service
[Unit]
Description=Flocker Control Service

[Service]
TimeoutStartSec=0
Environment="$env"
ExecStart=sh -c "$cmd"

[Install]
WantedBy=multi-user.target
EOF
  fi
  if [[ "$DISTRO" == "ubuntu" ]]; then
    cat << EOF > /etc/supervisor/conf.d/$service.conf
[program:$service]
environment=$env
command=sh -c "$cmd"
EOF
  fi

  cmd-enable-system-service flocker-control
}

# generic controller for the powerstrip containers
cmd-powerstrip() {
  # write adapters.yml
  cmd-powerstrip-config

  # write unit files for powerstrip-flocker and powerstrip
  cmd-configure-adapter $@
  cmd-configure-powerstrip

  # kick off services
  cmd-reload-process-supervisor
  cmd-start-system-service powerstrip-flocker
  cmd-start-system-service powerstrip
}

# kick off the zfs-agent so it writes /etc/flocker/volume.json
# then kill it before starting the powerstrip-adapter (which requires the file)
cmd-setup-zfs-agent() {
  cmd-flocker-zfs-agent $@

  # we need to start the zfs service so we have /etc/flocker/volume.json
  cmd-reload-process-supervisor
  cmd-start-system-service flocker-zfs-agent
  cmd-wait-for-file /etc/flocker/volume.json
  cmd-stop-system-service flocker-zfs-agent
}

cmd-fetch-config-from-disk-if-present() {
  # $1 is <your_ip>, $2 is <control_service>
  if [[ -f /etc/flocker/my_address ]]; then
      IP=`cat /etc/flocker/my_address`
  else
      IP=$1
  fi
  if [[ -f /etc/flocker/master_address ]]; then
      CONTROLIP=`cat /etc/flocker/master_address`
  else
      CONTROLIP=$2
  fi
  if [[ -z "$CONTROLIP" ]]; then
    CONTROLIP="127.0.0.1";
  fi
}

cmd-init() {
  # setup docker on /var/run/docker.real.sock
  cmd-configure-docker

  # make vagrant directory persistent
  cmd-copy-vagrant-dir
  # if we're not being passed IP addresses as arguments, see if we can fetch
  # them from disk
  cmd-fetch-config-from-disk-if-present $@

  # pull the images first
  cmd-docker-pull ubuntu:latest
  cmd-docker-pull clusterhq/powerstrip-flocker:latest
  cmd-docker-pull clusterhq/powerstrip:unix-socket
  cmd-docker-pull lmarsden/flocker-zfs-agent
  cmd-docker-pull lmarsden/flocker-control
}

cmd-master() {
  # common initialisation
  cmd-init

  # write unit files for both services
  cmd-flocker-control
  cmd-setup-zfs-agent $@

  cmd-powerstrip $@

  # kick off systemctl
  cmd-reload-process-supervisor
  cmd-start-system-service flocker-control
  cmd-start-system-service flocker-zfs-agent
}

cmd-minion() {
  # common initialisation
  cmd-init

  cmd-setup-zfs-agent $@

  cmd-powerstrip $@

  cmd-reload-process-supervisor
  cmd-start-system-service flocker-zfs-agent
}

usage() {
cat <<EOF
Usage:
install.sh master <your_ip> <control_service>
install.sh minion <your_ip> <control_service>
install.sh flocker-zfs-agent
install.sh block-start-flocker-zfs-agent <your_ip> <control_service>
install.sh flocker-control
install.sh get-flocker-uuid
install.sh configure-docker
install.sh configure-powerstrip
install.sh configure-adapter
install.sh start-adapter
install.sh start-powerstrip
install.sh powerstrip-config
install.sh help
EOF
  exit 1
}

main() {
  case "$1" in
  master)                   shift; cmd-master $@;;
  minion)                   shift; cmd-minion $@;;
  flocker-zfs-agent)        shift; cmd-flocker-zfs-agent $@;;
  block-start-flocker-zfs-agent) shift; cmd-block-start-flocker-zfs-agent $@;;
  flocker-control)  shift; cmd-flocker-control $@;;
  get-flocker-uuid)         shift; cmd-get-flocker-uuid $@;;
  configure-docker)         shift; cmd-configure-docker $@;;
  configure-powerstrip)     shift; cmd-configure-powerstrip $@;;
  configure-adapter)        shift; cmd-configure-adapter $@;;
  start-adapter)            shift; cmd-start-adapter $@;;
  start-powerstrip)         shift; cmd-start-powerstrip $@;;
  powerstrip-config)        shift; cmd-powerstrip-config $@;;
  docker-remove)            shift; cmd-docker-remove $@;;
  *)                        usage $@;;
  esac
}

# 

main "$@"
