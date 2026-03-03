#!/bin/bash
set -e

echo "Building container images with Podman..."

# IED Simulator
echo "Building IED Simulator..."
podman build -t localhost/ied-simulator:latest -f deployments/ied-simulator/Dockerfile deployments/ied-simulator/

# Edge Collector
echo "Building Edge Collector..."
podman build -t localhost/edge-collector:latest -f deployments/edge-collector/Dockerfile deployments/edge-collector/

# Kafka-InfluxDB Consumer
echo "Building Kafka-InfluxDB Consumer..."
podman build -t localhost/kafka-influxdb-consumer:latest -f deployments/kafka-influxdb-consumer/Dockerfile deployments/kafka-influxdb-consumer/

# PowSyBl API
echo "Building PowSyBl API..."
podman build -t localhost/powsybl-api:latest -f deployments/powsybl-api/Dockerfile deployments/powsybl-api/

echo "All images built successfully!"
podman images | grep localhost
