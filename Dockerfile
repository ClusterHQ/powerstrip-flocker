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
# Pre-install some requirements to make the next step hopefully faster
            pip install twisted==14.0.0 treq==0.2.1 service_identity pycrypto pyrsistent pyyaml==3.10

ADD         powerstripflocker.tac setup.py README.md /app/
ADD         powerstripflocker/* /app/powerstripflocker/

WORKDIR     /app

# Install requirements from the project's setup.py
RUN         python setup.py install

CMD         ["twistd", "-noy", "powerstripflocker.tac"]
