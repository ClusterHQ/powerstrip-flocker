#!/bin/bash

iptables-setup() {
  local allowserver="$1";
 
  iptables -F
  iptables -X
  # Setting default filter policy
  iptables -P INPUT DROP

  # Allow unlimited traffic on loopback
  iptables -A INPUT -i lo -j ACCEPT
   
  # Allow incoming ssh only
  iptables -A INPUT -p tcp --dport 22 -m state --state NEW,ESTABLISHED -j ACCEPT

  if [[ -n "$allowserver" ]]; then
    iptables -A INPUT -p tcp -s $allowserver --dport 80 -m state --state NEW,ESTABLISHED -j ACCEPT
    iptables -A INPUT -p tcp -s $allowserver --dport 4524 -m state --state NEW,ESTABLISHED -j ACCEPT
  fi

  # Disallow every other port
  iptables -A INPUT -j DROP
}

iptables-setup $@