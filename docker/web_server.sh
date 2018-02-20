#!/bin/bash
cp -r /home/onap/releng-testresults/display /usr/share/nginx/html

# nginx config
cp /home/onap/releng-testresults/docker/nginx.conf /etc/nginx/conf.d/
echo "daemon off;" >> /etc/nginx/nginx.conf

# supervisor config
cp /home/onap/releng-testresults/docker/supervisor.conf /etc/supervisor/conf.d/
