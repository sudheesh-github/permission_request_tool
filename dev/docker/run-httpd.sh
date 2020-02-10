#!/bin/bash

rm -rf /run/httpd/* /tmp/httpd*

/usr/sbin/postfix start
/usr/sbin/crond
exec /usr/sbin/apachectl -DFOREGROUND


