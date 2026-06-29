# Advanced Cluster Management

[Red Hat ACM Documentation](https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/latest)

Red Hat Advanced Cluster Management (ACM) provides multicluster lifecycle management, governance, and observability. Installing ACM also automatically installs the multicluster engine operator.

!!! note
    Only one ACM hub cluster can exist per OpenShift cluster.

## Prerequisites

- Hub cluster is installed and storage is configured
- Cluster administrator privileges

## Install the Operator via WebUI

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

## Install the Operator via YAML

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
  channel: release-2.12
  installPlanApproval: Automatic
  name: advanced-cluster-management
```

```bash
oc apply -f acm-operator.yaml
```

Wait for the operator to install:

```bash
oc get csv -n open-cluster-management -w
```

The `PHASE` should show `Succeeded`.

## Create the MultiClusterHub

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

## Verify the Installation

```bash
oc get pods -n open-cluster-management
oc get route multicloud-console -n open-cluster-management -o jsonpath='{.spec.host}'
```

## Add Provisioning

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

## Create InfraEnv

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

## Add Host Inventory via BMC

Once the InfraEnv is created, register bare metal hosts. ACM will automatically boot each host with the discovery ISO via Redfish virtual media — no manual ISO download or mounting is required.

!!! info "BMC Address Formats"
    The `bmc.address` field varies by hardware vendor:

    | Vendor       | Address Format                                                        |
    | ------------ | --------------------------------------------------------------------- |
    | HPE iLO      | `redfish-virtualmedia://{{ bmc_ip }}/redfish/v1/Systems/1`            |
    | Dell iDRAC   | `redfish-virtualmedia://{{ bmc_ip }}/redfish/v1/Systems/System.Embedded.1` |
    | Cisco CIMC   | `redfish-virtualmedia://{{ bmc_ip }}/redfish/v1/Systems/WZP12345678` |

    The system ID at the end of the path is specific to your hardware. You can discover it by querying the Redfish API:

    ```bash
    curl -sk https://{{ bmc_ip }}/redfish/v1/Systems/ -u {{ bmc_username }}:{{ bmc_password }} | jq '.Members'
    ```

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
      address: {{ bmc.address }}
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

## Provision the Spoke Cluster

Once all hosts are registered as agents, create the cluster resources to trigger installation.

!!! tip "Choosing a ClusterImageSet"
    The `imageSetRef.name` must reference a `ClusterImageSet` that exists on the hub. ACM installs several automatically. List available versions with:

    ```bash
    oc get clusterimageset
    ```

    Pick the version that matches your target OpenShift release (e.g., `img4.17.12-x86-64`).

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
    apiVIP: {{ api_vip }}
    ingressVIP: {{ ingress_vip }}
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

## Import an Existing Cluster

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
