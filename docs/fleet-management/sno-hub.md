# Hub Install (SNO)

A Single Node OpenShift (SNO) cluster runs the control plane and workloads on a single host. It serves as the management hub for the fleet. We use the [Assisted Installer](../standalone/assisted-installer.md) to provision this cluster.

## Prerequisites

* Complete the [prerequisites](../prerequisites/index.md)
* Set up the [installation host](../prerequisites/installation-host.md).

## Install Using the Assisted Installer

Follow the [Assisted Installer](../standalone/assisted-installer.md) guide with the following differences for SNO:

| Setting                        | Full Cluster (6-node)           | SNO Hub                        |
| ------------------------------ | ------------------------------- | ------------------------------ |
| Number of control plane nodes  | 3                               | **1 (Single Node OpenShift)**  |
| Number of workers              | 3                               | 0                              |
| Hosts to boot                  | All 6                           | 1                              |
| API VIP / Ingress VIP          | Separate VIP addresses          | Not required (uses host IP)    |
| Networking -> VIPs             | Fill in both                    | host IP                        |
| Installation time              | 30-45 minutes                   | 20-30 minutes                  |

!!! note
    Since SNO has a single node, the API and Ingress traffic goes directly to that node's IP. You do not need to configure VIPs in the Networking step — the installer will skip that section for SNO.

After installing the hub cluster, proceed to configure storage. 

Next: [Configure hub storage](hub-storage.md)
