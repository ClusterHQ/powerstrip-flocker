#!/bin/bash

export FLOCKER_CONTROL_PORT=${FLOCKER_CONTROL_PORT:=80}

# supported distributions: "ubuntu", "redhat" (means centos/fedora)
export DISTRO=${DISTRO:="ubuntu"}
export DOCKER=`which docker`

# on subsequent vagrant ups - vagrant has not mounted /vagrant/install.sh
# so we copy it into place
cmd-copy-vagrant-dir() {
  cp -r /vagrant /srv/vagrant
}


# copy insecure_private_key to /home/vagrant/.ssh/id_rsa and /root/.ssh/id_rsa
# this allows the vagrant and root user to do ssh root@otherhost
# the public key is already is authorized_keys for both root and vagrant
cmd-setup-ssh-keys() {
  cp /vagrant/insecure_private_key /root/.ssh/id_rsa
  chmod 600 /root/.ssh/id_rsa
  cp /vagrant/insecure_private_key /home/vagrant/.ssh/id_rsa
  chmod 600 /home/vagrant/.ssh/id_rsa
  chown vagrant:vagrant /home/vagrant/.ssh/id_rsa
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
    cat << EOF > /etc/default/docker
# Use DOCKER_OPTS to modify the daemon startup options.
DOCKER_OPTS="-H unix:///var/run/docker.real.sock --dns 8.8.8.8 --dns 8.8.4.4"
EOF
  fi
  cmd-restart-docker
  rm -f /var/run/docker.sock
}

cmd-enable-system-service() {
  if [[ "$DISTRO" == "redhat" ]]; then
    # create a link for the named systemd unit so it starts at boot
    ln -sf /etc/systemd/system/$1.service /etc/systemd/system/multi-user.target.wants/$1.service
  fi
  if [[ "$DISTRO" == "ubuntu" ]]; then
    # re-read the config files on disk (supervisorctl always has everything enabled)
    supervisorctl reread
  fi
}

cmd-reload-process-supervisor() {
  if [[ "$DISTRO" == "ubuntu" ]]; then
    supervisorctl reread
  fi
  if [[ "$DISTRO" == "redhat" ]]; then
    systemctl daemon-reload
  fi
}

cmd-start-system-service() {
  if [[ "$DISTRO" == "ubuntu" ]]; then
    supervisorctl start $1

    echo "supervisord start service $1"
  fi
  if [[ "$DISTRO" == "redhat" ]]; then
    # systemd requires services to be enabled before they're started, but
    # supervisor enables services by default (?)
    systemctl enable $1.service
    systemctl start $1.service

    echo "systemd start service $1"
  fi
}

cmd-stop-system-service() {
  if [[ "$DISTRO" == "ubuntu" ]]; then
    supervisorctl stop $1

    echo "supervisord stop service $1"
  fi
  if [[ "$DISTRO" == "redhat" ]]; then
    systemctl stop $1.service

    echo "systemd stop service $1"
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
  DOCKER_HOST="unix:///var/run/docker.real.sock" /usr/bin/docker stop $1 2>/dev/null || true
  DOCKER_HOST="unix:///var/run/docker.real.sock" /usr/bin/docker rm $1 2>/dev/null || true
}

# docker pull a named container
cmd-docker-pull() {
  echo "pull image $1";
  $DOCKER pull $1
}

# configure powerstrip-flocker adapter
cmd-configure-adapter() {
  local cmd="/srv/vagrant/install.sh start-adapter $IP $CONTROLIP"
  local service="powerstrip-flocker"

  echo "configure powerstrip adapter - $IP $CONTROLIP";

  if [[ "$DISTRO" == "redhat" ]]; then
    cat << EOF > /etc/systemd/system/$service.service
[Unit]
Description=Powerstrip Flocker Adapter
After=docker.service
Requires=docker.service

[Service]
ExecStart=/usr/bin/bash $cmd
ExecStop=/usr/bin/bash /srv/vagrant/install.sh docker-remove $service

[Install]
WantedBy=multi-user.target
EOF
  fi
  if [[ "$DISTRO" == "ubuntu" ]]; then
    cat << EOF > /etc/supervisor/conf.d/$service.conf
[program:$service]
command=/bin/bash $cmd
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
  docker run --name powerstrip-flocker \
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
ExecStart=/usr/bin/bash $cmd
ExecStop=/usr/bin/bash /srv/vagrant/install.sh docker-remove $service

[Install]
WantedBy=multi-user.target
EOF
  fi
  if [[ "$DISTRO" == "ubuntu" ]]; then
    cat << EOF > /etc/supervisor/conf.d/$service.conf
[program:$service]
command=/bin/bash $cmd
EOF
  fi

  cmd-enable-system-service $service
}

# the boot step for the powerstrip container - start without -d so process
# manager can manage the process
cmd-start-powerstrip() {
  rm -f /var/run/docker.sock
  cmd-docker-remove powerstrip
  DOCKER_HOST="unix:///var/run/docker.real.sock" \
  docker run --name powerstrip \
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
      chgrp ubuntu /var/run/docker.sock
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
  local cmd="/usr/bin/bash /srv/vagrant/install.sh block-start-flocker-zfs-agent $@"
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

  echo "test: $IP"
  echo "wait for docker socket before starting flocker-zfs-agent";

  while ! docker info; do echo "waiting for /var/run/docker.sock" && sleep 1; done;
  # TODO maaaaybe check for powerstrip container running here?
  /opt/flocker/bin/flocker-zfs-agent $IP $CONTROLIP
}


# configure control service with process manager
cmd-flocker-control-service() {
  local cmd="/opt/flocker/bin/flocker-control -p $FLOCKER_CONTROL_PORT"
  local service="flocker-control-service"

  echo "configure $service"

  if [[ "$DISTRO" == "redhat" ]]; then
    cat << EOF > /etc/systemd/system/$service.service
[Unit]
Description=Flocker Control Service

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

  cmd-enable-system-service flocker-control-service
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

  # setup docker on /var/run/docker.real.sock
  cmd-configure-docker
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
  # make vagrant directory persistent
  cmd-copy-vagrant-dir

  cmd-setup-ssh-keys
  # if we're not being passed IP addresses as arguments, see if we can fetch
  # them from disk
  cmd-fetch-config-from-disk-if-present $@

  # pull the images first
  cmd-docker-pull ubuntu:latest
  cmd-docker-pull clusterhq/powerstrip-flocker:latest
  cmd-docker-pull clusterhq/powerstrip:unix-socket
}

cmd-master() {
  # common initialisation
  cmd-init $@

  # write unit files for both services
  cmd-flocker-control-service
  cmd-setup-zfs-agent $@

  cmd-powerstrip $@

  # kick off systemctl
  cmd-reload-process-supervisor
  cmd-start-system-service flocker-control-service
  cmd-start-system-service flocker-zfs-agent
}

cmd-minion() {
  # common initialisation
  cmd-init $@

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
install.sh flocker-control-service
install.sh get-flocker-uuid
install.sh configure-docker
install.sh configure-powerstrip
install.sh configure-adapter
install.sh start-adapter
install.sh start-powerstrip
install.sh powerstrip-config
install.sh pocker-remove
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
  flocker-control-service)  shift; cmd-flocker-control-service $@;;
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
