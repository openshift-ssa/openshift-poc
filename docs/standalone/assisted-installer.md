# Assisted Installer

This guide covers installing a standalone multi-node cluster using the [Assisted Installer](https://console.redhat.com/openshift/assisted-installer/clusters). This should all be done from the installation host.

## Create the Cluster in the Assisted Installer

1. Navigate to [console.redhat.com/openshift/assisted-installer/clusters](https://console.redhat.com/openshift/assisted-installer/clusters)
2. Click **Create Cluster**
3. Configure the cluster details:
    - **Cluster name**: `poc`
    - **Base domain**: `ocp.basedomain.com`
    - **OpenShift version**: Latest stable
4. If your environment uses a proxy, configure the proxy settings:
    - HTTP Proxy
    - HTTPS Proxy
    - No Proxy list (see [Proxy Configuration](../prerequisites/networking.md#proxy-configuration))
    - Additional trust bundle (for MITM proxies)
5. Set the machine network to `10.0.0.0/28`

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

5. Boot all hosts from the ISO via BMC virtual media (Redfish, iLO, iDRAC)
6. Wait for all hosts to appear in the Assisted Installer UI

## Configure Hosts

Once all hosts are discovered:

1. Assign roles to each host:
    - 3 hosts as **Control Plane**
    - Remaining hosts as **Worker**
2. Configure static networking for each host:
    - IP Address (from your planned IP assignments)
    - Subnet mask: `255.255.255.240`
    - Gateway: `10.0.0.1`
    - DNS: Your DNS server(s)
    - NTP: Your NTP server
3. For bonded interfaces, configure the bond in the host's network settings:
    - Bond mode (LACP or active-backup)
    - Bond interfaces
    - VLAN (if applicable)

## Configure Cluster Networking

1. Set the **API VIP**: `10.0.0.2`
2. Set the **Ingress VIP**: `10.0.0.3`
3. Confirm the machine network is `10.0.0.0/28`
4. Cluster network: `10.128.0.0/14` (default)
5. Service network: `172.30.0.0/16` (default)

## Start the Installation

1. Review the cluster configuration
2. Click **Install Cluster**
3. Monitor progress in the UI or from the installation host:

```bash
# Download kubeconfig from the UI once available
export KUBECONFIG=~/poc/kubeconfig
oc get nodes
oc get clusterversion
```

Installation typically takes 30-45 minutes for a multi-node cluster.

## Validate the Install

```bash
oc login --server=https://api.poc.ocp.basedomain.com:6443 -u kubeadmin -p {{ password }}
oc get nodes
oc get clusterversion
oc get clusteroperators
```

Test container image pull connectivity:

```bash
oc debug node/{{ worker_node_name }} -- chroot /host \
  podman pull registry.redhat.io/ubi9/ubi:latest
```

Cleanup leftover pods:

```bash
oc delete pods --all-namespaces --field-selector=status.phase=Succeeded
oc delete pods --all-namespaces --field-selector=status.phase=Failed
```

For troubleshooting, see [Troubleshooting](troubleshooting.md).
