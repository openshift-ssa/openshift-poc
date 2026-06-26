# OpenShift PoC

Welcome to the OpenShift Proof of Concept documentation. This site provides the prerequisites and step-by-step instructions for installing Red Hat OpenShift Container Platform in on-premise environments.

## Getting Started

1. Review the [Prerequisites](prerequisites/index.md) to ensure your environment meets all requirements
2. Choose an [Installation](installation/index.md) method that fits your infrastructure
3. Complete [Post-Installation](post-installation/index.md) configuration for a production-ready cluster

## OpenShift Version

This documentation targets the latest stable release of OpenShift Container Platform (4.17).

## Cluster Architecture

OpenShift clusters consist of the following node types:

| Node Type       | Role                                                    | Minimum Count |
| --------------- | ------------------------------------------------------- | ------------- |
| Control Plane   | Runs the Kubernetes API, etcd, and cluster controllers  | 3             |
| Worker          | Runs application workloads                              | 2             |
| Infrastructure  | Runs cluster services (router, registry, monitoring)    | 3 (optional)  |

!!! note
    The term `master` is deprecated. Always use `control-plane` for control plane nodes.
