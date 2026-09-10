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

!!! warning "Verify the ACM Channel"
    The `release-2.17` channel above is an example and must match your OCP version. Before applying, verify the default channel: `oc get packagemanifest advanced-cluster-management -o jsonpath='{.status.defaultChannel}'`

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

### Create the AgentServiceConfig

The `AgentServiceConfig` CR enables the Assisted Service (part of multicluster engine) which handles bare metal cluster provisioning. Without it, the assisted-service pods won't deploy and InfraEnv creation will fail.

```yaml
apiVersion: agent-install.openshift.io/v1beta1
kind: AgentServiceConfig
metadata:
  name: agent
spec:
  databaseStorage:
    accessModes:
    - ReadWriteOnce
    resources:
      requests:
        storage: 10Gi
  filesystemStorage:
    accessModes:
    - ReadWriteOnce
    resources:
      requests:
        storage: 20Gi
  imageStorage:
    accessModes:
    - ReadWriteOnce
    resources:
      requests:
        storage: 50Gi
```

```bash
oc apply -f agentserviceconfig.yaml
```

Wait for the assisted-service pods to start:

```bash
oc get pods -n multicluster-engine -l app=assisted-service
```

!!! note
    In a connected environment, the Assisted Service automatically pulls the correct RHCOS images for each OpenShift version. In disconnected environments, you must also specify `spec.osImages` with references to locally mirrored ISO and rootFS images, and `spec.mirrorRegistryRef` pointing to a ConfigMap with your mirror registry configuration.

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

Repeat the following for each host in the spoke cluster.

#### 1. Create the BMC credentials Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: {{ hostname }}-bmc-secret
  namespace: {{ spoke_cluster_name }}
type: Opaque
stringData:
  username: {{ bmc_username }}
  password: {{ bmc_password }}
```

```bash
oc apply -f {{ hostname }}-bmc-secret.yaml
```

!!! tip
    Using `stringData:` lets you supply plain-text values. If you prefer `data:`, base64-encode first: `echo -n 'value' | base64`.

#### 2. Create the BareMetalHost

The `bmc.address` format is vendor-specific — use the correct scheme and system ID for your hardware:

=== "Dell iDRAC"

    ```yaml
    apiVersion: metal3.io/v1alpha1
    kind: BareMetalHost
    metadata:
      name: {{ hostname }}
      namespace: {{ spoke_cluster_name }}
      annotations:
        inspect.metal3.io/disabled: ""
      labels:
        infraenvs.agent-install.openshift.io: {{ spoke_cluster_name }}
    spec:
      online: true
      bootMACAddress: {{ boot_mac_address }}
      bmc:
        address: idrac-virtualmedia://{{ bmc_ip }}/redfish/v1/Systems/System.Embedded.1
        credentialsName: {{ hostname }}-bmc-secret
        disableCertificateVerification: true
      bootMode: UEFI
      rootDeviceHints:
        deviceName: /dev/sda
      automatedCleaningMode: disabled
    ```

    * The namespace for the InfraEnv and BareMetalHost must be the same

    !!! warning "Dell-Specific Requirements"
        - **iDRAC firmware** — virtual media via Redfish needs a reasonably current iDRAC. On iDRAC 9, use **4.40.00.00 or newer**; older firmware has flaky or missing virtual-media Redfish support. iDRAC 8 works but is more limited.
        - **Enterprise/Datacenter license** — virtual media requires it. The Express license does not expose the virtual media endpoint.

    !!! tip "`idrac-virtualmedia` vs `redfish-virtualmedia`"
        Ironic ships a Dell-optimized driver, `idrac-virtualmedia://`, which uses the same address format but handles Dell quirks (like boot-mode setting) more reliably. It is supported on OpenShift and is the recommended default for Dell hardware. Fall back to `redfish-virtualmedia://` only if you hit issues.

    !!! tip "`rootDeviceHints` on Dell"
        If these are PERC RAID setups, `/dev/sda` is usually correct. On NVMe or multi-disk boxes, prefer matching by `wwn` or `serialNumber` so you don't install to the wrong disk if a reboot reorders device names.

=== "HPE iLO"

    ```yaml
    apiVersion: metal3.io/v1alpha1
    kind: BareMetalHost
    metadata:
      name: {{ hostname }}
      namespace: {{ spoke_cluster_name }}
      annotations:
        inspect.metal3.io/disabled: ""
      labels:
        infraenvs.agent-install.openshift.io: {{ spoke_cluster_name }}
    spec:
      online: true
      bootMACAddress: {{ boot_mac_address }}
      bmc:
        address: redfish-virtualmedia://{{ bmc_ip }}/redfish/v1/Systems/1
        credentialsName: {{ hostname }}-bmc-secret
        disableCertificateVerification: true
      bootMode: UEFI
      rootDeviceHints:
        deviceName: /dev/sda
      automatedCleaningMode: disabled
    ```

=== "Lenovo XCC"

    ```yaml
    apiVersion: metal3.io/v1alpha1
    kind: BareMetalHost
    metadata:
      name: {{ hostname }}
      namespace: {{ spoke_cluster_name }}
      annotations:
        inspect.metal3.io/disabled: ""
      labels:
        infraenvs.agent-install.openshift.io: {{ spoke_cluster_name }}
    spec:
      online: true
      bootMACAddress: {{ boot_mac_address }}
      bmc:
        address: redfish-virtualmedia://{{ bmc_ip }}/redfish/v1/Systems/1
        credentialsName: {{ hostname }}-bmc-secret
        disableCertificateVerification: true
      bootMode: UEFI
      rootDeviceHints:
        deviceName: /dev/sda
      automatedCleaningMode: disabled
    ```

=== "Supermicro"

    ```yaml
    apiVersion: metal3.io/v1alpha1
    kind: BareMetalHost
    metadata:
      name: {{ hostname }}
      namespace: {{ spoke_cluster_name }}
      annotations:
        inspect.metal3.io/disabled: ""
      labels:
        infraenvs.agent-install.openshift.io: {{ spoke_cluster_name }}
    spec:
      online: true
      bootMACAddress: {{ boot_mac_address }}
      bmc:
        address: redfish-virtualmedia://{{ bmc_ip }}/redfish/v1/Systems/1
        credentialsName: {{ hostname }}-bmc-secret
        disableCertificateVerification: true
      bootMode: UEFI
      rootDeviceHints:
        deviceName: /dev/sda
      automatedCleaningMode: disabled
    ```

??? info "Field Reference"
    | Field                            | Description                                                                                                                                               |
    | -------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
    | `inspect.metal3.io/disabled`     | Annotation that skips Ironic hardware inspection. Required for ACM/InfraEnv host inventory so hosts register as agents instead of staying in `inspecting`. |
    | `bmc.address`                    | The `redfish-virtualmedia://` scheme avoids the provisioning-network requirement. The system ID at the end is vendor-specific (see tabs above).            |
    | `bootMACAddress`                 | MAC of the NIC the host boots from — **not** the BMC's MAC address.                                                                                      |
    | `disableCertificateVerification` | Usually required since BMCs ship with self-signed certs. Remove it if you have installed valid certificates.                                              |
    | `bootMode`                       | `UEFI` (default), `legacy`, or `UEFISecureBoot`.                                                                                                         |
    | `rootDeviceHints`                | Optional but recommended so Ironic installs to the correct disk. Can also match on `model`, `serialNumber`, `wwn`, `minSizeGigabytes`, etc.               |
    | `automatedCleaningMode`          | Set to `disabled` for POC to skip the disk-wipe step during provisioning. In production, consider leaving it enabled.                                     |

!!! tip "Discovering the System ID"
    If you're unsure of the system ID for your hardware, query the Redfish API:

    ```bash
    curl -sk https://{{ bmc_ip }}/redfish/v1/Systems/ \
      -u {{ bmc_username }}:{{ bmc_password }} | jq '.Members'
    ```

    See [Infrastructure — BMC / Out-of-Band Management](../../prerequisites/infrastructure.md#bmc-out-of-band-management) for more details.

```bash
oc apply -f {{ hostname }}-bmh.yaml
```

#### 3. Watch for hosts to boot and register as agents

```bash
oc get bmh -n {{ spoke_cluster_name }}
oc get agents -n {{ spoke_cluster_name }} -w
```

With `inspect.metal3.io/disabled` set, each host transitions through: `registering` → `available` (Ironic hardware inspection is skipped). ACM then boots the InfraEnv discovery ISO via virtual media so the host registers as an Agent. Once all hosts show as agents, you can create the cluster.

!!! warning
    Do not omit `inspect.metal3.io/disabled` on ACM/InfraEnv BareMetalHosts. Without it, the host stays in Ironic `inspecting` waiting for the IPA ramdisk instead of registering as an assisted-installer agent.

##### What happens during discovery boot

After the BareMetalHost is `available`, the Bare Metal Operator attaches the InfraEnv discovery ISO and powers the host on:

1. **Power on** — The Bare Metal Operator sends a power-on command via the BMC (iDRAC, iLO, XCC, etc.).
2. **Hardware POST** — The server runs its Power-On Self-Test. Depending on the hardware, this alone can take **5–15 minutes**.
3. **Virtual media boot** — The server boots the discovery ISO mounted by the BMC (not PXE / IPA inspection).
4. **Agent startup** — The assisted installer agent starts and applies any matching `NMStateConfig`.
5. **Call home** — The agent registers with the hub; `oc get agents` shows the new host.

!!! tip "Watch the BMC console"
    If you are waiting for the agent to come up, open the server's remote console (iDRAC, iLO, XCC) and watch the screen. Once you see the Linux kernel booting, the agent is only seconds away from starting. Long waits are often still in POST — not a hang.

### Approve Agents

Before creating the cluster, verify all agents are discovered and approve them. Agents must be approved before they can be assigned to a cluster.

1. List the agents and confirm all expected hosts appear:

  ```bash
  oc get agents -n {{ spoke_cluster_name }}
  ```

  You should see one agent per BareMetalHost.

2. Approve each agent:

  ```bash
  oc patch agent {{ agent_name }} -n {{ spoke_cluster_name }} \
    --type merge -p '{"spec":{"approved":true}}'
  ```

  Or approve all at once:

  ```bash
  for agent in $(oc get agents -n {{ spoke_cluster_name }} -o jsonpath='{.items[*].metadata.name}'); do
    oc patch agent "$agent" -n {{ spoke_cluster_name }} \
      --type merge -p '{"spec":{"approved":true}}'
  done
  ```

3. Set the role for each agent. You need exactly 3 `master` agents and the rest as `worker`:

  ```bash
  oc patch agent {{ agent_name }} -n {{ spoke_cluster_name }} \
    --type merge -p '{"spec":{"role":"master"}}'
  ```

  !!! tip
      If you don't set roles manually, the installer will auto-assign them, but it's better to be explicit — especially if your control plane nodes differ from your workers in hardware specs.

### Static IP Configuration (Optional)

If the spoke cluster nodes require static IPs (no DHCP), create `NMStateConfig` resources **before** the hosts boot. The InfraEnv injects these into the discovery ISO automatically.

```yaml
apiVersion: agent-install.openshift.io/v1beta1
kind: NMStateConfig
metadata:
  name: {{ hostname }}
  namespace: {{ spoke_cluster_name }}
  labels:
    infraenvs.agent-install.openshift.io: {{ spoke_cluster_name }}
spec:
  config:
    interfaces:
      - name: eno1
        type: ethernet
        state: up
        ipv4:
          enabled: true
          address:
            - ip: {{ host_ip }}
              prefix-length: {{ prefix_length }}
          dhcp: false
    dns-resolver:
      config:
        server:
          - {{ dns_server }}
    routes:
      config:
        - destination: 0.0.0.0/0
          next-hop-address: {{ gateway }}
          next-hop-interface: eno1
  interfaces:
    - name: eno1
      macAddress: {{ boot_mac_address }}
```

!!! note
    The `interfaces[].macAddress` at the bottom maps the NMState config to the correct physical NIC. The interface name (`eno1`) must match the actual NIC name on the host. If you are unsure, boot one host with DHCP first and check `ip link`.

### Create the Cluster

Once all agents are approved and showing `known` status, create the cluster resources to trigger installation.

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

2. Verify all agents are bound to the cluster before installation begins:

  ```bash
  oc get agents -n {{ spoke_cluster_name }} \
    -o custom-columns=NAME:.metadata.name,ROLE:.spec.role,APPROVED:.spec.approved,STATUS:.status.debugInfo.state
  ```

  All agents should show `approved: true` and status `binding` or `known`. If any agent shows `insufficient`, check its conditions:

  ```bash
  oc get agent {{ agent_name }} -n {{ spoke_cluster_name }} -o jsonpath='{.status.conditions}' | jq .
  ```

3. Monitor the installation:

  ```bash
  oc get agentclusterinstall {{ spoke_cluster_name }} -n {{ spoke_cluster_name }} -o jsonpath='{.status.conditions}' | jq .
  ```

  Or watch for completion:

  ```bash
  oc get agentclusterinstall {{ spoke_cluster_name }} -n {{ spoke_cluster_name }} -w
  ```

  The installation progresses through: `requirements-met` → `preparing-to-install` → `installing` → `finalizing` → `installed`. A typical 6-node cluster takes 45–60 minutes.

  !!! warning
      If the status stalls on `installing` for more than 90 minutes, check the individual host progress:
      ```bash
      oc get agents -n {{ spoke_cluster_name }} \
        -o custom-columns=NAME:.metadata.name,STAGE:.status.progress.currentStage,PROGRESS:.status.progress.progressInfo
      ```

4. Once complete, retrieve the kubeconfig and credentials:

  ```bash
  oc get secret {{ spoke_cluster_name }}-admin-kubeconfig -n {{ spoke_cluster_name }} \
    -o jsonpath='{.data.kubeconfig}' | base64 -d > {{ spoke_cluster_name }}-kubeconfig
  ```

  Retrieve the `kubeadmin` password:

  ```bash
  oc get secret {{ spoke_cluster_name }}-admin-password -n {{ spoke_cluster_name }} \
    -o jsonpath='{.data.password}' | base64 -d && echo
  ```

5. Verify the spoke cluster:

  ```bash
  oc --kubeconfig={{ spoke_cluster_name }}-kubeconfig get nodes
  oc --kubeconfig={{ spoke_cluster_name }}-kubeconfig get clusterversion
  oc --kubeconfig={{ spoke_cluster_name }}-kubeconfig get co
  ```

  All nodes should be `Ready`, the cluster version should match the target release, and all ClusterOperators should show `Available=True`.

6. Verify the spoke is managed by ACM:

  ```bash
  oc get managedcluster {{ spoke_cluster_name }}
  ```

  The cluster should show `HubAcceptedManagedCluster=True` and `ManagedClusterConditionAvailable=True`.

### Troubleshooting

| Symptom                                      | Likely Cause                                                       | Fix                                                                                                           |
| -------------------------------------------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| BMH stays in `registering`                   | BMC unreachable or credentials wrong                               | Verify `curl -sk https://{{ bmc_ip }}/redfish/v1/Systems/` works from the hub; check the Secret               |
| BMH stays in `inspecting`                    | Missing `inspect.metal3.io/disabled` (Ironic IPA inspect path)     | Add annotation `inspect.metal3.io/disabled: ""` on the BareMetalHost; confirm InfraEnv label and `online: true` |
| BMH `provisioning` but host doesn't boot ISO | Virtual media not supported or firmware too old                    | Check iDRAC/iLO firmware version; confirm Enterprise/Datacenter license (Dell)                                |
| Agent shows `insufficient`                   | Host doesn't meet minimum requirements (CPU, RAM, disk)            | Check `oc get agent <name> -o jsonpath='{.status.conditions}'`; resolve the flagged validation                |
| Agent shows `pending-for-input`              | Missing network config or role assignment                          | Approve the agent and assign a role (`master` or `worker`)                                                    |
| Install stalls at `installing`               | Host stuck downloading or writing to disk                          | Check per-host progress with `oc get agents` custom-columns; look for disk or network errors                  |
| Install fails with certificate errors        | BMC cert verification failing                                      | Ensure `disableCertificateVerification: true` is set on the BareMetalHost                                     |
| Spoke cluster not showing in ACM             | ManagedCluster not created or klusterlet not deployed              | Check `oc get managedcluster`; the ClusterDeployment should auto-create it                                    |
