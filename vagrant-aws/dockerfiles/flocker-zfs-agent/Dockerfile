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

# Replace iptables with... nothing.
RUN         ln -s /bin/true /usr/bin/iptables
RUN         ln -s /bin/true /usr/bin/iptables-save

# Alternative (because privileged)...
#RUN         apt-get -y iptables

ENV         updated_flocker 2015-03-14
RUN         cd /opt && git clone https://github.com/clusterhq/flocker && \
            cd flocker && git checkout containerized-handoff-coreos && \
            apt-get -y install python-setuptools python-dev

WORKDIR     /opt/flocker

# Install requirements from the project's setup.py
RUN         cd /opt/flocker && python setup.py install

CMD         ["/usr/local/bin/flocker-zfs-agent"]
