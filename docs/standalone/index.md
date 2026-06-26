# Standalone Cluster

For a standalone cluster installation, we use the agent-based installer from the installation host. This is for organizations who want to look at OpenShift as an application platform and/or to run virtual machines, without the complexity of fleet management.

## Process Overview

1. Complete all [prerequisites](../prerequisites/index.md)
2. Set up the [installation host](../prerequisites/installation-host.md)
3. Create the install configurations
4. Generate the agent ISO
5. Boot all nodes from the ISO
6. Monitor and complete installation

## Why Agent-Based Install?

| Benefit                | Description                                                      |
| ---------------------- | ---------------------------------------------------------------- |
| No external services   | No PXE, DHCP, or TFTP infrastructure required                    |
| Static IP support      | Network configuration built into the ISO                         |
| Single bootable ISO    | One artifact for all nodes                                       |
| Bare metal native      | Designed for on-premise bare metal environments                  |
| Bond/VLAN support      | Full NMState networking configuration                            |
