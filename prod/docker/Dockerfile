FROM centos:7


ENV http_proxy=proxy-am.shell.com:8080
ENV https_proxy=proxy-am.shell.com:8080

# Build commands
RUN groupadd -g 51515 u_051515;useradd -g 51515 -u 51515 -M -s /bin/bash -d /glb/home/s_tlstcs s_tlstcs
RUN yum swap -y fakesystemd systemd && \
    yum install -y systemd-devel
RUN yum install -y python-setuptools mysql-connector-python mysql-devel gcc python-devel git httpd-server httpd-devel httpd
RUN easy_install pip
RUN mkdir /opt/permission_request_application
RUN mkdir /opt/permission_request_application_files
WORKDIR /opt/permission_request_application
ADD httpd.conf /opt/permission_request_application/
ADD run-httpd.sh /opt/permission_request_application/
ADD requirements.txt /opt/permission_request_application/
RUN pip install -r requirements.txt
ADD . /opt/permission_request_application

ENV http_proxy=""
ENV https_proxy=""


RUN mv /etc/httpd/conf/httpd.conf /etc/httpd/conf/httpd.conf.orig

RUN cp /opt/permission_request_application/httpd.conf /etc/httpd/conf/httpd.conf
RUN cp /opt/permission_request_application/run-httpd.sh /run-httpd.sh
RUN chmod -v +x /run-httpd.sh
EXPOSE 80

#CMD ["/usr/sbin/apachectl", "-D", "FOREGROUND"]
CMD ["/run-httpd.sh"]
 


