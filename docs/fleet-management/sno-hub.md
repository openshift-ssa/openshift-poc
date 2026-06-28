# Hub Install (SNO)

[Assisted Installer for OpenShift Container Platform Official Documentation](https://docs.redhat.com/en/documentation/assisted_installer_for_openshift_container_platform/latest/html/installing_openshift_container_platform_with_the_assisted_installer/index)

A Single Node OpenShift (SNO) cluster runs the control plane and workloads on a single host. It serves as the management hub for the fleet. We use the [Assisted Installer](https://console.redhat.com/openshift/assisted-installer/clusters) to provision this cluster.

## Prerequisites

Complete the [prerequisites](../prerequisites/index.md) and set up the [installation host](../prerequisites/installation-host.md).

## DNS

All DNS records point to the single node's IP address. No load balancer is required.

| Record                                         | Value           |
| ---------------------------------------------- | --------------- |
| `api.{{ cluster_name }}.{{ base_domain }}`     | `{{ node_ip }}` |
| `api-int.{{ cluster_name }}.{{ base_domain }}` | `{{ node_ip }}` |
| `*.apps.{{ cluster_name }}.{{ base_domain }}`  | `{{ node_ip }}` |

A reverse PTR record for the node IP is also required.

## Install Using the Assisted Installer

Follow the [Assisted Installer](../standalone/assisted-installer.md) guide with the following differences for SNO:

| Setting                        | Full Cluster (6-node)           | SNO Hub                        |
| ------------------------------ | ------------------------------- | ------------------------------ |
| Number of control plane nodes  | 3                               | **1 (Single Node OpenShift)**  |
| Number of workers              | 3                               | 0                              |
| Hosts to boot                  | All 6                           | 1                              |
| API VIP / Ingress VIP          | Separate VIP addresses          | Not required (uses node IP)    |
| Networking -> VIPs             | Fill in both                    | Leave empty                    |
| Installation time              | 30-45 minutes                   | 20-30 minutes                  |

!!! note
    Since SNO has a single node, the API and Ingress traffic goes directly to that node's IP. You do not need to configure VIPs in the Networking step — the installer will skip that section for SNO.

## Validate the Install

```bash
oc login --server=https://api.{{ cluster_name }}.{{ base_domain }}:6443 -u kubeadmin -p {{ password }}
oc get nodes
oc get clusterversion
oc get clusteroperators
```

Cleanup leftover pods:

```bash
oc delete pods --all-namespaces --field-selector=status.phase=Succeeded
oc delete pods --all-namespaces --field-selector=status.phase=Failed
```

Next: [Configure hub storage](hub-storage.md)
