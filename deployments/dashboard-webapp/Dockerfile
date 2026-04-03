FROM docker.io/nginx:alpine

# Copy the HTML dashboard
COPY index.html /usr/share/nginx/html/

# Create custom nginx.conf with writable PID path
RUN echo 'pid /tmp/nginx.pid;' > /etc/nginx/nginx.conf && \
    echo 'error_log /dev/stderr info;' >> /etc/nginx/nginx.conf && \
    echo 'events { worker_connections 1024; }' >> /etc/nginx/nginx.conf && \
    echo 'http {' >> /etc/nginx/nginx.conf && \
    echo '    include /etc/nginx/mime.types;' >> /etc/nginx/nginx.conf && \
    echo '    default_type application/octet-stream;' >> /etc/nginx/nginx.conf && \
    echo '    access_log /dev/stdout;' >> /etc/nginx/nginx.conf && \
    echo '    sendfile on;' >> /etc/nginx/nginx.conf && \
    echo '    keepalive_timeout 65;' >> /etc/nginx/nginx.conf && \
    echo '    server {' >> /etc/nginx/nginx.conf && \
    echo '        listen 8080;' >> /etc/nginx/nginx.conf && \
    echo '        server_name _;' >> /etc/nginx/nginx.conf && \
    echo '        location / {' >> /etc/nginx/nginx.conf && \
    echo '            root /usr/share/nginx/html;' >> /etc/nginx/nginx.conf && \
    echo '            index index.html;' >> /etc/nginx/nginx.conf && \
    echo '            add_header Access-Control-Allow-Origin *;' >> /etc/nginx/nginx.conf && \
    echo '        }' >> /etc/nginx/nginx.conf && \
    echo '    }' >> /etc/nginx/nginx.conf && \
    echo '}' >> /etc/nginx/nginx.conf

# Run as non-root user - create required directories and set permissions
# OpenShift runs with random UID but group root, so we need group read permissions
RUN mkdir -p /var/cache/nginx/client_temp \
             /var/cache/nginx/proxy_temp \
             /var/cache/nginx/fastcgi_temp \
             /var/cache/nginx/uwsgi_temp \
             /var/cache/nginx/scgi_temp && \
    chgrp -R 0 /usr/share/nginx/html && \
    chmod -R g=u /usr/share/nginx/html && \
    chmod -R 644 /usr/share/nginx/html/* && \
    chgrp -R 0 /var/cache/nginx && \
    chmod -R g=u /var/cache/nginx

USER nginx

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
