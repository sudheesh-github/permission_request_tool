#!/bin/bash

/usr/sbin/postfix start
exec /usr/sbin/crond -n


