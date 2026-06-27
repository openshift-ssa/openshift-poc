# Hub Install (SNO)

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

## Create the Cluster in the Assisted Installer

1. Navigate to [console.redhat.com/openshift/assisted-installer/clusters](https://console.redhat.com/openshift/assisted-installer/clusters)
2. Click **Create Cluster**
3. Configure the cluster details:
    - **Cluster name**: `hub`
    - **Base domain**: `ocp.basedomain.com`
    - **OpenShift version**: Latest stable
    - **Install single node OpenShift (SNO)**: Enabled
4. If your environment uses a proxy, configure the proxy settings:
    - HTTP Proxy
    - HTTPS Proxy
    - No Proxy list
    - Additional trust bundle (for MITM proxies)

## Generate and Boot the Discovery ISO

1. On the **Host discovery** step, click **Generate Discovery ISO**
2. Configure the ISO:
    - **SSH public key**: Contents of `~/.ssh/ocp.pub`
    - **Proxy settings** (if applicable)
3. Download the discovery ISO or copy the download URL
4. Serve the ISO from the installation host:

```bash
podman run -d --name iso-http \
  -p 8080:8080 \
  -v ~/discovery-iso.iso:/var/www/html/discovery-iso.iso:Z \
  registry.redhat.io/rhel9/httpd-24:9.6
```

5. Boot the host from the ISO via BMC virtual media (Redfish, iLO, iDRAC)
6. Wait for the host to appear in the Assisted Installer UI

## Configure Networking

Once the host is discovered, configure its network settings:

1. Click on the host in the UI
2. Configure static networking:
    - **IP Address**: `10.0.0.3`
    - **Subnet mask**: `255.255.255.240`
    - **Gateway**: `10.0.0.1`
    - **DNS**: Your DNS server(s)
    - **NTP**: Your NTP server
3. Confirm the machine network is `10.0.0.0/28`

## Start the Installation

1. Review the cluster configuration
2. Click **Install Cluster**
3. Monitor progress in the UI or from the installation host:

```bash
# Download kubeconfig from the UI once available
export KUBECONFIG=~/hub/kubeconfig
oc get nodes
oc get clusterversion
```

Installation typically takes 20-30 minutes for SNO.

## Validate the Install

```bash
oc login --server=https://api.hub.ocp.basedomain.com:6443 -u kubeadmin -p {{ password }}
oc get nodes
oc get clusterversion
oc get clusteroperators
```

Test connectivity:

```bash
oc debug node/{{ node_name }} -- chroot /host \
  podman pull registry.redhat.io/ubi9/ubi:latest
```

Cleanup leftover pods:

```bash
oc delete pods --all-namespaces --field-selector=status.phase=Succeeded
oc delete pods --all-namespaces --field-selector=status.phase=Failed
```

Next: [Configure hub storage](hub-storage.md)
