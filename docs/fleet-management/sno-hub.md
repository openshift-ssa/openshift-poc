# Single Node OpenShift (Hub)

The hub cluster is a Single Node OpenShift (SNO) installation that serves as the management plane for your fleet. Install it using the Assisted Installer.

## Steps

1. Access the [Assisted Installer](https://console.redhat.com/openshift/assisted-installer/clusters)
2. Select **Single Node OpenShift** as the cluster topology
3. Generate and boot the discovery ISO on the hub node
4. Complete the installation
5. Verify the cluster

```bash
export KUBECONFIG=~/hub-cluster/auth/kubeconfig
oc get nodes
oc get clusterversion
```

---

## Details

### SNO Requirements

Single Node OpenShift runs the control plane and workloads on a single node with higher resource requirements:

| Resource | Minimum   |
| -------- | --------- |
| vCPU     | 8         |
| RAM      | 32 GB     |
| Storage  | 120 GB    |

### DNS Records for SNO

Since there is only one node, both API and Ingress point to the same IP:

| Record                               | Type | Value       |
| ------------------------------------ | ---- | ----------- |
| api.{cluster_name}.{base_domain}     | A    | Node IP     |
| api-int.{cluster_name}.{base_domain} | A    | Node IP     |
| *.apps.{cluster_name}.{base_domain}  | A    | Node IP     |

### Load Balancer

No load balancer is required for SNO. All traffic routes directly to the single node.

### Installation via Assisted Installer

The process is the same as the [standalone Assisted Installer](../standalone/assisted-installer.md) flow with one difference: select **SNO** as the topology. Only one host needs to boot from the discovery ISO.

Installation typically takes 20-30 minutes for SNO.
