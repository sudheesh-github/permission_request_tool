FROM centos:7

# This Docker image is for running cron

ENV http_proxy=proxy-am.shell.com:8080
ENV https_proxy=proxy-am.shell.com:8080

# Build commands
RUN groupadd -g 51515 u_051515;useradd -g 51515 -u 51515 -M -s /bin/bash -d /glb/home/s_tlstcs s_tlstcs
RUN yum swap -y fakesystemd systemd && \
    yum install -y systemd-devel
RUN yum install -y python-setuptools mysql-connector-python mysql-devel gcc python-devel git cronie crontabs postfix
RUN easy_install pip
RUN mkdir -p /opt/permission_request
RUN mkdir -p /opt/permission_request_files
WORKDIR /opt/permission_request
ADD run-cron.sh /opt/permission_request/
ADD requirements.txt /opt/permission_request/
RUN pip install -r requirements.txt
ADD . /opt/permission_request/

ENV http_proxy=""
ENV https_proxy=""

RUN cp /opt/permission_request/run-cron.sh /run-cron.sh
RUN chmod -v +x /run-cron.sh
EXPOSE 25

#CMD ["/usr/sbin/crond -n"]
CMD ["/run-cron.sh"]

