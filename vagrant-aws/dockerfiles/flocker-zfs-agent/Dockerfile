FROM        ubuntu:14.04

# Last build date - this can be updated whenever there are security updates so
# that everything is rebuilt
ENV         security_updates_as_of 2014-07-06

# Install security updates and required packages
RUN         apt-get -qy update && \
            apt-get -qy upgrade && \
            apt-get -qy install python-pip && \
            apt-get -qy install python-dev && \
            apt-get -qy install python-pyasn1 && \
            apt-get -qy install libyaml-dev && \
            apt-get -qy install libffi-dev && \
            apt-get -qy install libssl-dev && \
            apt-get -qy install wget && \
# Pre-install some requirements to make the next step hopefully faster
            pip install twisted==14.0.0 treq==0.2.1 service_identity pycrypto pyrsistent pyyaml==3.10


RUN         cd ~/ && \
            wget https://pypi.python.org/packages/source/m/machinist/machinist-0.2.0.tar.gz && \
            tar zxfv machinist-0.2.0.tar.gz && \
            cd machinist-0.2.0 && \
            python setup.py install

RUN         cd ~/ && \
            wget https://pypi.python.org/packages/source/e/eliot/eliot-0.6.0.tar.gz && \
            tar zxfv eliot-0.6.0.tar.gz && \
            cd eliot-0.6.0 && \
            python setup.py install

RUN         apt-get -qy install git

RUN         apt-get -y install build-essential gawk alien fakeroot linux-headers-$(uname -r) zlib1g-dev uuid-dev libblkid-dev libselinux-dev parted lsscsi dh-autoreconf git

RUN         cd ~/ && \
            git clone https://github.com/zfsonlinux/spl && \
            cd spl && \
            git checkout 47af4b76ffe72457166e4abfcfe23848ac51811a && \
            ./autogen.sh && \
            ./configure && \
            make && \
            make deb && \
            sudo dpkg -i *.deb

RUN         cd ~/ && \
            git clone https://github.com/zfsonlinux/zfs && \
            cd zfs && \
            git checkout d958324f97f4668a2a6e4a6ce3e5ca09b71b31d9 && \
            ./autogen.sh && \
            ./configure && \
            make && \
            make deb && \
            sudo dpkg -i *.deb

# Replace iptables with... nothing.
RUN         ln -s /bin/true /usr/bin/iptables
RUN         ln -s /bin/true /usr/bin/iptables-save

# Alternative (because privileged)...
#RUN         apt-get -y iptables

RUN         cd /opt && git clone https://github.com/clusterhq/flocker && \
            cd flocker && git checkout edf19adc2b620562f75f5c1e065d253344a5152d && \
            apt-get -y install python-setuptools python-dev

WORKDIR     /opt/flocker

# Install requirements from the project's setup.py
RUN         cd /opt/flocker && python setup.py install

CMD         ["/usr/local/bin/flocker-zfs-agent"]
