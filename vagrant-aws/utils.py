from pipes import quote
import subprocess
import yaml

config = yaml.load(open("settings.yml"))

def runSSH(ip, command):
    command = 'ssh -i %s %s@%s %s' % (config["private_key_path"],
            config["remote_server_username"],
            ip, " ".join(map(quote, command)))
    return subprocess.check_output(command, shell=True)

def pushConfig(text, instances):
    f = open("master_address", "w")
    f.write(text)
    f.close()

    print "Written master address"
    for (externalIP, internalIP) in instances:
        runSSH(externalIP, ['sudo', 'mkdir', '-p', '/etc/flocker'])
        scp = "scp -i %s master_address %s@%s:/tmp/master_address" % (
                config["private_key_path"], config["remote_server_username"], externalIP,)
        subprocess.check_output(scp, shell=True)
        runSSH(externalIP, ['sudo', 'mv', '/tmp/master_address', '/etc/flocker/master_address'])
        print "Pushed master address to %s" % (externalIP,)
    print "Finished telling all nodes about the master."
