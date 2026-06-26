# Standalone Cluster

For a standalone cluster installation, we recommend using the [Assisted Installer](https://console.redhat.com/openshift/assisted-installer/clusters) available in the [Red Hat Hybrid Cloud Console](https://console.redhat.com).

The Assisted Installer is a guided, web-based experience that handles the complexity of OpenShift installation while giving you full control over your cluster configuration.

## Process Overview

1. Complete all [prerequisites](../prerequisites/index.md)
2. Access the [Assisted Installer](https://console.redhat.com/openshift/assisted-installer/clusters)
3. Configure cluster details
4. Generate and boot the discovery ISO
5. Configure networking
6. Complete installation

## Why Assisted Installer?

| Benefit                | Description                                                      |
| ---------------------- | ---------------------------------------------------------------- |
| Guided experience      | Step-by-step wizard with validation at each stage                |
| Pre-flight checks      | Validates hardware, networking, and DNS before installation      |
| No external services   | No need for PXE, DHCP, or TFTP infrastructure                   |
| Flexible topologies    | Supports multi-node, compact (3-node), and single node clusters  |
| Bare metal & vSphere   | Works with physical servers and virtual machines                  |
