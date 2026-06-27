# Assisted Installer

[Assisted Installer for OpenShift Container Platform Official Documentation](https://docs.redhat.com/en/documentation/assisted_installer_for_openshift_container_platform/latest/html/installing_openshift_container_platform_with_the_assisted_installer/index)

This guide covers installing a standalone multi-node cluster using the [Assisted Installer](https://console.redhat.com/openshift/assisted-installer/clusters). This should all be done from the installation host. You should have completed the [prerequisites](../prerequisites/index.md) and you should have that information handy. You should also have a valid ssh key available. 

## Create the Cluster in the Assisted Installer

To get started with the assisted installer, proceed to the [Red Hat Hybrid Cloud Console](https://console.redhat.com/openshift/assisted-installer/clusters). Click on "Create Cluster". If an item in the details below isn't specifically referenced, that means to leave the default. 

### Cluster details

- Put in the cluster name
- Put in the Base domain
- Choose the OpenShift Version (ensure compatibility, especially with storage CSI driver)
- Choose your CPU architecture (x86_64 is typical)
- Choose No platform integration
- Number of control plane nodes should be selected based on the install type you are doing: 
    - 1 (Single Node OpenShift)
    - 3 (highly available cluster)
- Choose Hosts' network configuration to be "Static IP, bridges and bonds" (unless you allow DHCP, which is rare)
- No Encryption

-> Click Next

### Static network configurations

- Select IPv4
- If you are using a vlan, click "Use VLAN" checkbox, and enter the Machine Subnet VLAN value. 
- Enter DNS values
- Enter the Machine Subnet values
- Enter the Default gateway

-> Click Next

### Host specific configurations

- If using a bond, click the "Use bond" checkbox
    - Bond type is typically 802.3ad (LACP)
- Enter the mac addresses for the NICs in the bond using the Host NICs - MAC Address values
- Enter the IP address for the host
- If you are doing a full cluster install, repeat this process for all the hosts by using the "Add another host configuration" button. 

--> Click Next

### Operators

Don't preinstall any operators. 

--> Click Next

### Host discovery

- Click on the "Add hosts" button at the top of the page
- For "Provisioning type", select "Full image file - Download a self-contained ISO"
- Add the SSH public key 
- If you have a specific [proxy](../prerequisites/networking.md#proxy-configuration) configuration, use the "Show proxy settings" checkbox to enable the view and enter the information. 
- If you have a [MITM proxy](../prerequisites/networking.md#how-to-determine-if-you-have-a-mitm-proxy) which reencrypts traffic, click the "Configure cluster-wide trusted certificates" and add the MITM root/intermediate cert. 
- Click "Generate Discovery ISO" and save the ISO file. 

#### BMC Install

- If you are using a BMC web interface to create the cluster, save the ISO file locally and attach it. 
- The web interfaces for BMC installs of this nature can be finicky. If you have a web server somewhere, host it there. Or use the Discovery ISO URL. 

### Waiting for host

- Boot the host(s) with the ISO
    - for a SNO install, wait for the single host to present itself
    - for a full cluster install, wait for all hosts to come up in the list
- Update the Hostname(s) and Role for all the hosts
- Wait for all the status on the host to be "Ready"

--> Click Next

### Storage

- For each host in the list, ensure the correct disk is selected for the installation disk. 
- Deselect format for any network based storage

--> Click Next

### Networking

- Select Cluster-managed networking
- Select Network type of Open Virtual Networking (OVN)
- Select the correct machine network
- Fill in the API VIP IP
- Fill in the Ingress VIP IP
- Use advanced networking is only used to change the pod and service network. Leave it. 
- Leave "Use the same host discovery SSH key" checkbox selected
- In the Host Inventory, you should be able to see all kinds of host information. Check it out. 

--> Next

### Custom Manifests

- No custom manifests

--> Next

### Review and Create

--> Install cluster

### Watch Progress

- Installation progress will show the steps being taken
- You can view the hosts activity in the host inventory table
- The cluster summary provides all the cluster information
- Installation typically takes 30-45 minutes for a multi-node cluster

Wait for it...

- Copy the Web Console URL
- User name is kubeadmin
- Copy the Password
- Login to the Web Console
- Wait for the Operators to finish updating and everything to be green. 

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

For troubleshooting, see [Troubleshooting](troubleshooting.md).
