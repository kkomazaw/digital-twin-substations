FROM lfedge/fledge:latest

# Install additional dependencies for IEC 61850 and Redis
USER root

RUN apt-get update && apt-get install -y \
    python3-pip \
    git \
    cmake \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages for custom plugins
RUN pip3 install --no-cache-dir \
    redis \
    requests \
    paho-mqtt

# Copy custom North plugin for Redis Streams
COPY plugins/fledge-north-redis/ /usr/local/fledge/python/fledge/plugins/north/redis_stream/

# Copy South plugin for HTTP polling (IED simulator)
COPY plugins/fledge-south-http/ /usr/local/fledge/python/fledge/plugins/south/http_poll/

# Copy startup configuration
COPY config/ /usr/local/fledge/data/etc/

# Set proper permissions
RUN chown -R fledge:fledge /usr/local/fledge/python/fledge/plugins/ \
    && chown -R fledge:fledge /usr/local/fledge/data/

USER fledge

EXPOSE 8081 1995 6683

CMD ["/usr/local/fledge/bin/fledge", "start"]
