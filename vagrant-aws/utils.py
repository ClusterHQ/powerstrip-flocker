from pipes import quote
import subprocess

def runSSH(ip, command):
    command = 'ssh ubuntu@%s %s' % (ip, " ".join(map(quote, command)))
    return subprocess.check_output(command, shell=True)

def pushConfig(text, instances):
    f = open("master_address", "w")
    f.write(text)
    f.close()

    print "Written master address"
    for (externalIP, internalIP) in instances:
        runSSH(externalIP, ['sudo', 'mkdir', '-p', '/etc/flocker'])
        scp = "scp master_address hybrid@%s:/tmp/master_address" % (externalIP,)
        subprocess.check_output(scp, shell=True)
        runSSH(externalIP, ['sudo', 'mv', '/tmp/master_address', '/etc/flocker/master_address'])
        print "Pushed master address to %s" % (externalIP,)
    print "Nodelist written"
