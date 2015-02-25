# -*- mode: ruby -*-
# vi: set ft=ruby :

# This requires Vagrant 1.6.2 or newer (earlier versions can't reliably
# configure the Fedora 20 network stack).
Vagrant.require_version ">= 1.6.2"

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

ENV['VAGRANT_DEFAULT_PROVIDER'] = 'virtualbox'

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.box = "vagrant-powerstrip-flocker-demo"
  config.vm.box_url = "http://storage.googleapis.com/experiments-clusterhq/powerstrip-flocker-demo/tutorial-flocker-tutorial-0.3.2%2Bdoc1-1786-gbcc7bb4.box"

  if Vagrant.has_plugin?("vagrant-cachier")
    config.cache.scope = :box
  end

  config.vm.define "node1" do |node1|
    node1.vm.network :private_network, :ip => "172.16.255.250"
    node1.vm.hostname = "node1"
    node1.vm.provision "shell", inline: <<SCRIPT
bash /vagrant/install.sh master 172.16.255.250 172.16.255.250
SCRIPT
  end

  config.vm.define "node2" do |node2|
    node2.vm.network :private_network, :ip => "172.16.255.251"
    node2.vm.hostname = "node2"
    node2.vm.provision "shell", inline: <<SCRIPT
bash /vagrant/install.sh minion 172.16.255.251 172.16.255.250
SCRIPT
  end
end
