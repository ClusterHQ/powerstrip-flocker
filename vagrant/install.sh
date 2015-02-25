#!/bin/bash

export FLOCKER_CONTROL_PORT=${FLOCKER_CONTROL_PORT:=80}

cmd-get-flocker-uuid() {
  cat /etc/flocker/volume.json | sed 's/.*"uuid": "//' | sed 's/"}//'
}

cmd-configure-docker() {
  cat << EOF > /etc/sysconfig/docker-network
DOCKER_NETWORK_OPTIONS=-H unix:///var/run/docker.real.sock
EOF
  systemctl restart docker
  rm -f /var/run/docker.sock
}


cmd-link-systemd-target() {
	ln -sf /etc/systemd/system/$1.service /etc/systemd/system/multi-user.target.wants/$1.service
}

cmd-docker-remove() {
	DOCKER_HOST="unix:///var/run/docker.real.sock" /usr/bin/docker stop $1 2>/dev/null || true
	DOCKER_HOST="unix:///var/run/docker.real.sock" /usr/bin/docker rm $1 2>/dev/null || true
}

cmd-docker-pull() {
	DOCKER_HOST="unix:///var/run/docker.real.sock" /usr/bin/docker pull $1
}

cmd-configure-adapter() {
  local IP="$1";
  local CONTROLIP="$2";
  cat << EOF > /etc/systemd/system/powerstrip-flocker.service
[Unit]
Description=Powerstrip Flocker Adapter
After=docker.service
Requires=docker.service

[Service]
ExecStart=/usr/bin/bash /vagrant/install.sh start-adapter $IP $CONTROLIP

[Install]
WantedBy=multi-user.target
EOF

	cmd-link-systemd-target powerstrip-flocker
}

cmd-start-adapter() {
	cmd-docker-remove powerstrip-flocker
  local IP="$1";
  local CONTROLIP="$2";
  local HOSTID=$(cmd-get-flocker-uuid)
  DOCKER_HOST="unix:///var/run/docker.real.sock" \
  docker run -d --name powerstrip-flocker \
    --expose 80 \
    -e "MY_NETWORK_IDENTITY=$IP" \
    -e "FLOCKER_CONTROL_SERVICE_BASE_URL=http://$CONTROLIP:80/v1" \
    -e "MY_HOST_UUID=$HOSTID" \
    clusterhq/powerstrip-flocker:latest
}

cmd-configure-powerstrip() {
    cat << EOF > /etc/systemd/system/powerstrip.service
[Unit]
Description=Powerstrip Server
After=powerstrip-flocker.service
Requires=powerstrip-flocker.service

[Service]
ExecStart=/usr/bin/bash /vagrant/install.sh start-powerstrip

[Install]
WantedBy=multi-user.target
EOF

	cmd-link-systemd-target powerstrip
}

cmd-start-powerstrip() {
	rm -f /var/run/docker.sock
	cmd-docker-remove powerstrip
  DOCKER_HOST="unix:///var/run/docker.real.sock" \
  docker run -d --name powerstrip \
    -v /var/run:/host-var-run \
    -v /etc/powerstrip-demo/adapters.yml:/etc/powerstrip/adapters.yml \
    --link powerstrip-flocker:flocker \
    clusterhq/powerstrip:unix-socket
  sleep 5
  chgrp vagrant /var/run/docker.sock
}

cmd-powerstrip-config() {
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

cmd-flocker-zfs-agent() {
  local IP="$1";
  local CONTROLIP="$2";

  if [[ -z "$CONTROLIP" ]]; then
    CONTROLIP="127.0.0.1";
  fi

  cat << EOF > /etc/systemd/system/flocker-zfs-agent.service
[Unit]
Description=Flocker ZFS Agent

[Service]
TimeoutStartSec=0
ExecStart=/usr/sbin/setenforce 0 && /opt/flocker/bin/flocker-zfs-agent $IP $CONTROLIP

[Install]
WantedBy=multi-user.target
EOF

	cmd-link-systemd-target flocker-zfs-agent
}

cmd-flocker-control-service() {
  cat << EOF > /etc/systemd/system/flocker-control-service.service
[Unit]
Description=Flocker Control Service

[Service]
TimeoutStartSec=0
ExecStart=/opt/flocker/bin/flocker-control -p $FLOCKER_CONTROL_PORT

[Install]
WantedBy=multi-user.target
EOF

	cmd-link-systemd-target flocker-control-service
}

cmd-powerstrip() {
	# write adapters.yml
  cmd-powerstrip-config

  # setup docker on /var/run/docker.real.sock
  cmd-configure-docker

  # write unit files for powerstrip-flocker and powerstrip
  cmd-configure-adapter $@
  cmd-configure-powerstrip

  # pull the images first
	cmd-docker-pull clusterhq/powerstrip-flocker:latest
	cmd-docker-pull clusterhq/powerstrip:unix-socket

  # kick off systemctl
  systemctl daemon-reload
  systemctl enable powerstrip-flocker.service
  systemctl enable powerstrip.service
  systemctl start powerstrip-flocker.service
  systemctl start powerstrip.service
}

cmd-master() {

	# write unit files for both services
  cmd-flocker-control-service
  cmd-flocker-zfs-agent $@

  # kick off systemctl
  systemctl daemon-reload
  systemctl enable flocker-control-service.service
  systemctl enable flocker-zfs-agent.service
  systemctl start flocker-control-service.service
  systemctl start flocker-zfs-agent.service
  cmd-powerstrip $@
}

cmd-minion() {
  cmd-flocker-zfs-agent $@
  systemctl daemon-reload
  systemctl enable flocker-zfs-agent.service
  systemctl start flocker-zfs-agent.service
  cmd-powerstrip $@
}

usage() {
cat <<EOF
Usage:
install.sh master
install.sh minion
install.sh flocker-zfs-agent
install.sh flocker-control-service
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
