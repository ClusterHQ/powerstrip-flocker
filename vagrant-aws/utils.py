import os
from pipes import quote
import subprocess

def runSSH(ip, command):
    command = 'ssh -p 2222 -i ~/HybridDeployment/credentials/master_key hybrid@%s %s' % (ip, " ".join(map(quote, command)))
    return subprocess.check_output(command, shell=True)


def constructConfig(instances):
    values = dict(
        ip1=instances[0][0],
        privateip1=instances[0][1],
        ip2=instances[1][0],
        privateip2=instances[1][1],
    )
    for n in range(1, 8):
        values["secret%d" % (n,)] = os.urandom(16).encode("hex")

    yaml = """cluster_uuid: hc-vagrantcluster
control_panel: my.vagrantcluster.hybrid-cloud.com
demo_mode: 1
elastichosts_instances:
  somewhere:
    node001:
      cloud_uuid: node001
      short_uuid: node001
      internal_uuid: node001
      freebsd_version: '9.1'
      ip: %(ip1)s
      private_ip: %(privateip1)s
      provider: private
    node002:
      cloud_uuid: node002
      short_uuid: node002
      internal_uuid: node002
      freebsd_version: '9.1'
      ip: %(ip2)s
      private_ip: %(privateip2)s
      provider: private
friendly_name: laptop
ips:
  node001: %(ip1)s
  node002: %(ip2)s
secrets:
  ADMINAPI_KEY: %(secret1)s
  HYBRIDCLUSTER_PASS: %(secret2)s
  JAIL_MYSQL_PASS: %(secret3)s
  JSONAPI_KEY: %(secret4)s
  MYSQL_PASS: %(secret5)s
  MYSQL_ROOT_PASS: %(secret6)s
  SPREAD_KEY: %(secret7)s
site_domain: vagrantcluster.hybrid-cloud.com
""" % values
    return yaml


def pushConfig(yaml, instances):
    f = open("config.yml", "w")
    f.write(yaml)
    f.close()

    print "Written config.yml"

    homedir = os.path.expanduser('~')
    nodelist = open("%s/.hybrid_client/nodelist" % (homedir,), "w")

    for (externalIP, internalIP) in instances:
        runSSH(externalIP, ['sudo', 'mkdir', '-p', '/etc/cluster'])

        scp = "scp -P 2222 -i ~/HybridDeployment/credentials/master_key config.yml hybrid@%s:/tmp/config.yml" % (externalIP,)
        subprocess.check_output(scp, shell=True)

        runSSH(externalIP, ['sudo', 'mv', '/tmp/config.yml', '/etc/cluster/config.yml'])

        print "Pushed config.yml to %s" % (externalIP,)
        nodelist.write("%s\n" % (externalIP,))

    # TODO: Create mysql-hybridcluster, but before we do that, we need to actually start supervisord.

    #nodeForDatabase = instances[0][0]
    #runSSH(nodeForDatabase, ['sudo', 'bash', '-c', 'echo \'self.json_api.jsonrpc_addDatabase("hybridcluster")\' | /opt/HybridCluster/bin/hcl repl sitejuggler'])

    nodelist.close()
    print "Nodelist written"

    # TODO: Set hostnames appropriately, and configure /etc/hosts

