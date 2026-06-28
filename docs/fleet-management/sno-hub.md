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

## Create the Cluster in the Assisted Installer

To get started, proceed to the [Red Hat Hybrid Cloud Console](https://console.redhat.com/openshift/assisted-installer/clusters). Click on "Create Cluster". If an item below isn't specifically referenced, leave the default.

### Cluster details

- Put in the cluster name (e.g., `hub`)
- Put in the Base domain
- Choose the OpenShift Version
- Choose your CPU architecture (x86_64 is typical)
- Choose No platform integration
- Number of control plane nodes: **1 (Single Node OpenShift)**
- Choose Hosts' network configuration to be "Static IP, bridges and bonds"
- No Encryption

-> Click Next

### Static network configurations

- Select IPv4
- If you are using a vlan, click "Use VLAN" checkbox and enter the Machine Subnet VLAN value
- Enter DNS values
- Enter the Machine Subnet values (e.g., `10.0.0.0/28`)
- Enter the Default gateway (e.g., `10.0.0.1`)

-> Click Next

### Host specific configurations

- If using a bond, click the "Use bond" checkbox
    - Bond type is typically 802.3ad (LACP)
- Enter the MAC addresses for the NICs
- Enter the IP address for the host

-> Click Next

### Operators

Don't preinstall any operators.

-> Click Next

### Host discovery

- Click on the "Add hosts" button at the top of the page
- For "Provisioning type", select "Full image file - Download a self-contained ISO"
- Add the SSH public key (from `~/.ssh/ocp.pub`)
- If you have a specific [proxy](../prerequisites/networking.md#proxy-configuration) configuration, use the "Show proxy settings" checkbox
- If you have a [MITM proxy](../prerequisites/networking.md#how-to-determine-if-you-have-a-mitm-proxy), click "Configure cluster-wide trusted certificates" and add the cert
- Click "Generate Discovery ISO" and save the ISO file

#### BMC Install

- If you are using a BMC web interface, save the ISO file locally and attach it
- The web interfaces for BMC installs can be finicky. If you have a web server, host it there. Or use the Discovery ISO URL.

### Waiting for host

- Boot the host with the ISO
- Wait for the single host to present itself in the UI
- Update the Hostname and Role
- Wait for the status to be "Ready"

-> Click Next

### Storage

- Ensure the correct disk is selected for the installation disk
- Deselect format for any network based storage

-> Click Next

### Networking

- Select Cluster-managed networking
- Select Network type of Open Virtual Networking (OVN)
- Select the correct machine network
- Leave "Use the same host discovery SSH key" checkbox selected

-> Click Next

### Custom Manifests

- No custom manifests

-> Click Next

### Review and Create

-> Install cluster

### Watch Progress

- Installation progress will show the steps being taken
- Installation typically takes 20-30 minutes for SNO

Wait for it...

- Copy the Web Console URL
- User name is kubeadmin
- Copy the Password
- Login to the Web Console
- Wait for the Operators to finish updating and everything to be green

## Validate the Install

```bash
oc login --server=https://api.hub.ocp.basedomain.com:6443 -u kubeadmin -p {{ password }}
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
