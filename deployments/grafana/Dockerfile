FROM docker.io/grafana/grafana:10.2.0

USER root

# Install Infinity datasource plugin to a system-wide location
RUN grafana cli --pluginsDir="/usr/share/grafana/plugins" plugins install yesoreyeram-infinity-datasource

# Use only the system plugin directory to avoid emptyDir volume conflicts
ENV GF_PATHS_PLUGINS="/usr/share/grafana/plugins"

USER grafana

EXPOSE 3000
