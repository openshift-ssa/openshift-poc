# Assisted Installer

The Assisted Installer provides a streamlined installation experience through the Red Hat Hybrid Cloud Console. For this environment, all nodes are bare metal with static IP configurations.

## Steps

1. Log in to [console.redhat.com](https://console.redhat.com)
2. Navigate to **OpenShift** > **Clusters** > **Create cluster** > **Datacenter**
3. Select **Interactive** under the Assisted Installer option
4. Configure cluster details
5. Generate the discovery ISO
6. Mount the ISO via BMC virtual media and boot all nodes
7. Configure static networking for each host
8. Start installation

---

## Details

### Cluster Configuration

Provide the following during cluster setup:

| Field             | Description             | Example        |
| ----------------- | ----------------------- | -------------- |
| Cluster name      | Name for your cluster   | ocp-poc        |
| Base domain       | Base DNS domain         | example.com    |
| OpenShift version | Latest stable release   | 4.17           |
| CPU architecture  | x86_64 or aarch64      | x86_64         |
| Network type      | OVN-Kubernetes (default)| OVN-Kubernetes |

### Pull Secret

Your pull secret is automatically associated with your Red Hat account in the Assisted Installer. No manual configuration needed.

### Discovery ISO

Generate and download the discovery ISO from the Assisted Installer UI. Mount the ISO on each bare metal node via BMC virtual media (Redfish, iLO, iDRAC, or IPMI).

Once nodes boot from the ISO, they will register with the Assisted Installer and appear in the UI. The installer runs pre-flight validations on each host to verify:

- Minimum CPU and memory requirements
- Disk requirements
- Network connectivity between hosts
- DNS resolution for API and Ingress
- NTP synchronization

### Static IP Configuration

Since there is no DHCP in this environment, select **Static IP, bridges, and bonds** in the Assisted Installer network configuration step.

For each host, provide:

| Field         | Example           |
| ------------- | ----------------- |
| MAC Address   | aa:bb:cc:dd:ee:00 |
| IP Address    | 10.0.0.10         |
| Subnet Prefix | 24                |
| Gateway       | 10.0.0.1          |
| DNS Server    | 10.0.0.2          |

The Assisted Installer uses NMState to apply the static network configurations to each host based on MAC address matching.

!!! tip
    Have your [static IP assignment table](../prerequisites/networking.md) ready before starting this step. Mismatched MAC addresses are a common source of installation failures.

### API and Ingress VIPs

Provide the Virtual IP addresses for the cluster. These must be unused IPs on the machine network:

| VIP         | Purpose                     | DNS Record                          |
| ----------- | --------------------------- | ----------------------------------- |
| API VIP     | Kubernetes API access       | api.{cluster_name}.{base_domain}    |
| Ingress VIP | Application traffic routing | *.apps.{cluster_name}.{base_domain} |

!!! note
    For single node OpenShift (SNO), the node IP serves as both the API and Ingress endpoint. No VIPs are needed.

### Installation

Once all validations pass, click **Install cluster**. Monitor progress in the console. Installation typically takes 30-45 minutes for a multi-node cluster.

After installation completes, download the `kubeconfig` and note the `kubeadmin` password from the console.

```bash
export KUBECONFIG=~/ocp-poc/auth/kubeconfig
oc get nodes
oc get clusterversion
```

### Troubleshooting

The Assisted Installer provides logs and event timelines in the UI. For deeper troubleshooting:

```bash
ssh core@<node-ip>
journalctl -b -f -u bootkube.service
```

Common issues in bare metal static IP environments:

| Issue                         | Cause                                      | Resolution                          |
| ----------------------------- | ------------------------------------------ | ----------------------------------- |
| Host not registering          | Incorrect network config or MAC mismatch   | Verify MAC addresses and IP config  |
| DNS validation fails          | DNS records not created or not resolving    | Verify A records and wildcard entry |
| NTP validation fails          | Firewall blocking NTP or no NTP source     | Open port 123/UDP to NTP servers    |
| Insufficient disk             | Boot disk too small or wrong disk selected | Ensure 120 GB+ disk is available    |
