#!/bin/bash
iptables-start() {
  iptables -F
  iptables -X
  # Setting default filter policy
  iptables -P INPUT DROP

  # Allow unlimited traffic on loopback
  iptables -A INPUT -i lo -j ACCEPT

  # Allow incoming ssh only
  iptables -A INPUT -p tcp --dport 22 -m state --state NEW,ESTABLISHED -j ACCEPT
}

iptables-middle() {
  local allowserver="$1";
  if [[ -n "$allowserver" ]]; then
    iptables -A INPUT -p tcp -s $allowserver --dport 80 -m state --state NEW,ESTABLISHED -j ACCEPT
    iptables -A INPUT -p tcp -s $allowserver --dport 4524 -m state --state NEW,ESTABLISHED -j ACCEPT
  fi
}
iptables-finish() {
  # Disallow every other port
  iptables -A INPUT -j DROP
}

iptables-start
for X in `cat /etc/flocker/minions`; do iptables-middle $X; done
iptables-finish
