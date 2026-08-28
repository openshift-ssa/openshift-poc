# Hub and Spoke

For fleet management, we recommend starting with a Single Node OpenShift (SNO) installation as the hub cluster, then installing Red Hat Advanced Cluster Management (ACM) to manage your cluster fleet at scale.

## Process Overview

1. Complete all [prerequisites](../../prerequisites/index.md)
2. Set up the [installation host](../../prerequisites/installation-host.md)
3. Install the SNO hub cluster
4. Install storage on the hub
5. Install Advanced Cluster Management
6. Use ACM to provision bare metal spoke clusters

## Why Hub and Spoke?

| Benefit               | Description                                               |
| --------------------- | --------------------------------------------------------- |
| Centralized control   | Manage all clusters from a single pane of glass           |
| Consistent policy     | Enforce governance and security policies across the fleet |
| Scalable provisioning | Create new clusters on demand through ACM                 |
| Lifecycle management  | Upgrade and maintain clusters centrally                   |
| Observability         | Unified view of cluster health and compliance             |

---

## Install the Hub Cluster (SNO)

A Single Node OpenShift (SNO) cluster runs the control plane and workloads on a single host. It serves as the management hub for the fleet. We use the [Assisted Installer](../assisted-installer.md) to provision this cluster.

### Prerequisites

- Complete the [prerequisites](../../prerequisites/index.md)
- Set up the [installation host](../../prerequisites/installation-host.md)

### Install Using the Assisted Installer

Follow the [Assisted Installer](../assisted-installer.md) guide with the following differences for SNO:

| Setting                       | Full Cluster (6-node)  | SNO Hub                       |
| ----------------------------- | ---------------------- | ----------------------------- |
| Number of control plane nodes | 3                      | **1 (Single Node OpenShift)** |
| Number of workers             | 3                      | 0                             |
| Hosts to boot                 | All 6                  | 1                             |
| API VIP / Ingress VIP         | Separate VIP addresses | Not required (uses host IP)   |
| Networking -> VIPs            | Fill in both           | host IP                       |
| Installation time             | 30-45 minutes          | 20-30 minutes                 |

!!! note
    Since SNO has a single node, the API and Ingress traffic goes directly to that node's IP. You do not need to configure VIPs in the Networking step — the installer will skip that section for SNO.

---

## Configure Hub Storage

[OpenShift Storage - Persistent Storage using LVMS](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/storage/persistent-storage-using-local-storage#persistent-storage-using-lvms)

After installing the SNO hub cluster, configure storage before installing ACM. These examples are for environments without existing external storage on the hub node.

### Install LVM Storage Operator

1. Go to Ecosystem -> Software Catalog -> filter for "LVM Storage" -> click the tile
2. Click Install
3. Leave all the defaults and click Install
4. Wait for the Operator to install

Label the node as a storage node **only if you are installing OpenShift Data Foundation** (see the optional section below). LVM Storage does not use this label.

### Create LVM Storage

1. Go to Ecosystem -> Installed Operators -> click "LVM Storage"
2. Click on the "LVMCluster" tab and then click "Create LVMCluster"
3. Switch to YAML view and update the path for your data disk:

  ```yaml
  apiVersion: lvm.topolvm.io/v1alpha1
  kind: LVMCluster
  metadata:
    name: local-storage-lvm-cluster
    namespace: openshift-storage
  spec:
    storage:
      deviceClasses:
        - name: local-storage
          default: true
          fstype: xfs
          deviceSelector:
            paths:
              - /dev/nvme0n1
          thinPoolConfig:
            name: thin-pool-1
            sizePercent: 90
            overprovisionRatio: 10
            chunkSizeCalculationPolicy: Static
            metadataSizeCalculationPolicy: Host
  ```

4. Click Create

### OPTIONAL — Install OpenShift Data Foundation (Object Storage)

[OpenShift Data Foundation Documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_data_foundation/latest)

This is only needed if you are planning to use ODF as part of your OPP subscription. ODF is used here specifically for object storage required by [MultiCluster Observability](../../configure-the-cluster/multicluster-observability.md). If your storage provider does not offer object storage, you can deploy MinIO instead. See [Using MinIO](../../configure-the-cluster/multicluster-observability.md#using-minio).

Label the hub node for ODF before creating the StorageCluster:

```bash
oc label node {{ node_name }} cluster.ocs.openshift.io/openshift-storage=
```

1. Go to Ecosystem -> Software Catalog -> filter for "OpenShift Data Foundation" -> click the tile
2. Click Install
3. Leave all the defaults and click Install
4. Wait for the Operator to install
5. Go to Ecosystem -> Installed Operators -> click "OpenShift Data Foundation"
6. Click on the "StorageCluster" tab and then click "Create StorageCluster"
7. Switch to YAML view and paste:

  ```yaml
  apiVersion: ocs.openshift.io/v1
  kind: StorageCluster
  metadata:
    name: mcog-storagecluster
    namespace: openshift-storage
  spec:
    arbiter: {}
    encryption:
      keyRotation:
        schedule: '@weekly'
      kms: {}
    externalStorage: {}
    managedResources:
      cephObjectStoreUsers: {}
      cephCluster: {}
      cephBlockPools: {}
      cephNonResilientPools: {}
      cephObjectStores: {}
      cephFilesystems: {}
      cephRBDMirror: {}
      cephToolbox: {}
      cephDashboard: {}
      cephConfig: {}
    multiCloudGateway:
      dbStorageClassName: lvms-local-storage
      reconcileStrategy: standalone
    resourceProfile: balanced
  ```

8. Click Create

### Verify Storage

```bash
oc get lvmcluster -n openshift-storage
oc get storagecluster -n openshift-storage
oc get storageclass
oc get pods -n openshift-storage
```

Ensure the LVM StorageClass is set as default:

```bash
oc get storageclass | grep default
```

---

## Install Advanced Cluster Management

[Red Hat ACM Documentation](https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/latest)

Red Hat Advanced Cluster Management (ACM) provides multicluster lifecycle management, governance, and observability. Installing ACM also automatically installs the multicluster engine operator.

!!! note
    Only one ACM hub cluster can exist per OpenShift cluster.

### Prerequisites

- Hub cluster is installed and storage is configured
- Cluster administrator privileges

### Install the Operator via WebUI

1. Go to Ecosystem -> Software Catalog -> filter for "Advanced Cluster Management" -> click the tile
2. Click Install
3. Leave all the defaults and click Install
4. Wait for the Operator to install
5. Go to Ecosystem -> Installed Operators -> click "Advanced Cluster Management for Kubernetes"
6. Click on the "MultiClusterHub" tab and then click "Create MultiClusterHub"
7. Leave all the defaults and click Create

!!! note
    It can take up to 10 minutes for the hub to finish deploying all components.

8. Wait for the status to show `Running`

### Install the Operator via YAML

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: open-cluster-management
---
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: open-cluster-management
  namespace: open-cluster-management
spec:
  targetNamespaces:
    - open-cluster-management
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: acm-operator-subscription
  namespace: open-cluster-management
spec:
  sourceNamespace: openshift-marketplace
  source: redhat-operators
  channel: release-2.17
  installPlanApproval: Automatic
  name: advanced-cluster-management
```

!!! note
    The ACM channel must match your OCP version. Verify the default channel: `oc get packagemanifest advanced-cluster-management -o jsonpath='{.status.defaultChannel}'`

```bash
oc apply -f acm-operator.yaml
```

Wait for the operator to install:

```bash
oc get csv -n open-cluster-management -w
```

The `PHASE` should show `Succeeded`.

### Create the MultiClusterHub

```yaml
apiVersion: operator.open-cluster-management.io/v1
kind: MultiClusterHub
metadata:
  name: multiclusterhub
  namespace: open-cluster-management
spec: {}
```

```bash
oc apply -f multiclusterhub.yaml
```

Monitor the status:

```bash
oc get mch -n open-cluster-management -w
```

The status should show `Running`.

### Verify ACM

```bash
oc get pods -n open-cluster-management
oc get route multicloud-console -n open-cluster-management -o jsonpath='{.spec.host}'
```

### Enable Bare Metal Provisioning

Enable bare metal provisioning for spoke cluster deployment:

```yaml
apiVersion: metal3.io/v1alpha1
kind: Provisioning
metadata:
  name: provisioning-configuration
spec:
  provisioningNetwork: "Disabled"
  watchAllNamespaces: true
```

```bash
oc apply -f provisioning.yaml
```

### Import an Existing Cluster

To import an existing cluster (one not provisioned by ACM) into the hub:

1. Create the ManagedCluster resource on the hub:

  ```yaml
  apiVersion: cluster.open-cluster-management.io/v1
  kind: ManagedCluster
  metadata:
    name: {{ managed_cluster_name }}
  spec:
    hubAcceptsClient: true
  ```

  ```bash
  oc apply -f managed-cluster.yaml
  ```

2. Wait for ACM to generate the import resources:

  ```bash
  oc get secret -n {{ managed_cluster_name }} | grep import
  ```

3. Extract the import YAML and apply it on the target cluster:

  ```bash
  oc get secret {{ managed_cluster_name }}-import -n {{ managed_cluster_name }} \
    -o jsonpath='{.data.import\.yaml}' | base64 -d > import.yaml

  oc apply -f import.yaml --kubeconfig={{ managed_cluster_kubeconfig }}
  ```

4. Verify the managed cluster is connected:

  ```bash
  oc get managedcluster {{ managed_cluster_name }}
  ```

  The `HubAcceptedManagedCluster` condition should be `True` and the cluster should show as `Available`.

---

## Provision a Bare Metal Spoke Cluster

[Red Hat ACM Documentation - Host Inventory](https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/latest/html/clusters/cluster_mce_overview#host-inventory-intro)

This section covers using ACM to provision a new bare metal OpenShift cluster. ACM handles the entire lifecycle: booting hosts with a discovery ISO via BMC, registering them as agents, and installing the cluster.

### Prerequisites

- ACM is installed and configured on the hub cluster (see above)
- Bare metal provisioning is enabled
- BMC credentials available for all target hosts
- [DNS records](../../prerequisites/dns.md) configured for the spoke cluster (API, Ingress, nodes)

### Create InfraEnv

The InfraEnv defines the discovery environment for spoke cluster hosts. ACM uses this to generate a discovery ISO and automatically attach it to hosts via BMC.

1. Create the namespace for the spoke cluster:

  ```bash
  oc create namespace {{ spoke_cluster_name }}
  ```

2. Create the pull secret in the spoke namespace:

  ```bash
  oc create secret generic pullsecret-{{ spoke_cluster_name }} \
    --from-file=.dockerconfigjson=~/pull-secret.txt \
    --type=kubernetes.io/dockerconfigjson \
    -n {{ spoke_cluster_name }}
  ```

3. Create the InfraEnv:

  ```yaml
  apiVersion: agent-install.openshift.io/v1beta1
  kind: InfraEnv
  metadata:
    name: {{ spoke_cluster_name }}
    namespace: {{ spoke_cluster_name }}
  spec:
    cpuArchitecture: x86_64
    ipxeScriptType: DiscoveryImageAlways
    nmStateConfigLabelSelector:
      matchLabels:
        infraenvs.agent-install.openshift.io: {{ spoke_cluster_name }}
    pullSecretRef:
      name: pullsecret-{{ spoke_cluster_name }}
    sshAuthorizedKey: {{ public_key }}
  ```

  ```bash
  oc apply -f infraenv.yaml
  ```

### Add Host Inventory via BMC

Once the InfraEnv is created, register bare metal hosts. ACM will automatically boot each host with the discovery ISO via Redfish virtual media — no manual ISO download or mounting is required.

!!! info "BMC Address Formats"
    The `bmc.address` field varies by hardware vendor. See [Infrastructure — BMC / Out-of-Band Management](../../prerequisites/infrastructure.md#bmc-out-of-band-management) for the address format table and instructions on discovering the system ID via the Redfish API.

Repeat the following for each host in the spoke cluster:

1. Create the BMC secret:

  ```bash
  oc create secret generic {{ hostname }}-bmc-secret \
    --from-literal=username={{ bmc_username }} \
    --from-literal=password={{ bmc_password }} \
    -n {{ spoke_cluster_name }}
  ```

2. Create the BareMetalHost:

  ```yaml
  apiVersion: metal3.io/v1alpha1
  kind: BareMetalHost
  metadata:
    name: {{ hostname }}
    namespace: {{ spoke_cluster_name }}
    labels:
      infraenvs.agent-install.openshift.io: {{ spoke_cluster_name }}
  spec:
    bmc:
      address: {{ bmc_address }}
      credentialsName: "{{ hostname }}-bmc-secret"
      disableCertificateVerification: true
    bootMACAddress: {{ boot_mac_address }}
    online: true
    automatedCleaningMode: disabled
  ```

  ```bash
  oc apply -f {{ hostname }}-bmh.yaml
  ```

3. Watch for hosts to boot and register as agents:

  ```bash
  oc get bmh -n {{ spoke_cluster_name }}
  oc get agents -n {{ spoke_cluster_name }} -w
  ```

  Each host will transition through: `registering` -> `inspecting` -> `available`. Once all hosts show as agents, you can create the cluster.

### Create the Cluster

Once all hosts are registered as agents, create the cluster resources to trigger installation.

!!! tip "Choosing a ClusterImageSet"
    The `imageSetRef.name` must reference a `ClusterImageSet` that exists on the hub. ACM installs several automatically. List available versions with:

    ```bash
    oc get clusterimageset
    ```

    Pick the version that matches your target OpenShift release (e.g., `img{{ ocp_release }}-x86-64`).

1. Create the ClusterDeployment and AgentClusterInstall:

  ```yaml
  apiVersion: hive.openshift.io/v1
  kind: ClusterDeployment
  metadata:
    name: {{ spoke_cluster_name }}
    namespace: {{ spoke_cluster_name }}
  spec:
    baseDomain: {{ base_domain }}
    clusterName: {{ spoke_cluster_name }}
    controlPlaneConfig:
      servingCertificates: {}
    installed: false
    clusterInstallRef:
      group: extensions.hive.openshift.io
      kind: AgentClusterInstall
      name: {{ spoke_cluster_name }}
      version: v1beta1
    platform:
      agentBareMetal:
        agentSelector:
          matchLabels:
            infraenvs.agent-install.openshift.io: {{ spoke_cluster_name }}
    pullSecretRef:
      name: pullsecret-{{ spoke_cluster_name }}
  ---
  apiVersion: extensions.hive.openshift.io/v1beta1
  kind: AgentClusterInstall
  metadata:
    name: {{ spoke_cluster_name }}
    namespace: {{ spoke_cluster_name }}
  spec:
    clusterDeploymentRef:
      name: {{ spoke_cluster_name }}
    imageSetRef:
      name: {{ cluster_image_set }}
    networking:
      clusterNetwork:
        - cidr: 10.128.0.0/14
          hostPrefix: 23
      serviceNetwork:
        - 172.30.0.0/16
      machineNetwork:
        - cidr: {{ machine_network_cidr }}
    provisionRequirements:
      controlPlaneAgents: 3
      workerAgents: 3
    sshPublicKey: {{ public_key }}
    apiVIPs:
      - {{ api_vip }}
    ingressVIPs:
      - {{ ingress_vip }}
  ```

  ```bash
  oc apply -f cluster-deployment.yaml
  ```

2. Monitor the installation:

  ```bash
  oc get agentclusterinstall {{ spoke_cluster_name }} -n {{ spoke_cluster_name }} -w
  ```

  The status will progress through `requirements-met` -> `installing` -> `installed`.

3. Once complete, retrieve the kubeconfig and credentials:

  ```bash
  oc get secret {{ spoke_cluster_name }}-admin-kubeconfig -n {{ spoke_cluster_name }} \
    -o jsonpath='{.data.kubeconfig}' | base64 -d > {{ spoke_cluster_name }}-kubeconfig

  oc get secret {{ spoke_cluster_name }}-admin-password -n {{ spoke_cluster_name }} \
    -o jsonpath='{.data.password}' | base64 -d
  ```

4. Verify the spoke cluster:

  ```bash
  oc --kubeconfig={{ spoke_cluster_name }}-kubeconfig get nodes
  oc --kubeconfig={{ spoke_cluster_name }}-kubeconfig get clusterversion
  ```
