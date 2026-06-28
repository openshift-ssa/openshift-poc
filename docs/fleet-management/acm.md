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

```yaml
apiVersion: agent-install.openshift.io/v1beta1
kind: InfraEnv
metadata:
  name: lab
  namespace: lab
spec:
  agentLabels:
    agentclusterinstalls.extensions.hive.openshift.io/location: ktown
  cpuArchitecture: x86_64
  ipxeScriptType: DiscoveryImageAlways
  nmStateConfigLabelSelector:
    matchLabels:
      infraenvs.agent-install.openshift.io: lab
  pullSecretRef:
    name: pullsecret-lab
  sshAuthorizedKey: {{ public_key }}
```

```bash
oc apply -f infraenv.yaml
```

## Adding Host Inventory via Redfish

1. Create the BMC secret:

  ```bash
  oc create secret generic {{ hostname }}-bmc-secret \
    --from-literal=username=admin \
    --from-literal=password=your-bmc-password \
    -n {{ infraenv_namespace }}
  ```

2. Create the BareMetalHost:

  ```yaml
  apiVersion: metal3.io/v1alpha1
  kind: BareMetalHost
  metadata:
    name: {{ hostname }}-bmh
    namespace: {{ infraenv_namespace }}
    labels:
      infraenvs.agent-install.openshift.io: {{ infraenv_namespace }}
  spec:
    bmc:
      address: redfish-virtualmedia://{{ bmc_ip }}/redfish/v1/
      credentialsName: "{{ hostname }}-bmc-secret"
      disableCertificateVerification: true
    bootMACAddress: "aa:bb:cc:dd:ee:ff"
    online: false
  ```

3. Apply it:

  ```bash
  oc apply -f {{ hostname }}-bmh.yaml
  ```

## Import a Managed Cluster

To import an existing cluster into ACM:

1. Create the ManagedCluster resource on the hub:

  ```yaml
  apiVersion: cluster.open-cluster-management.io/v1
  kind: ManagedCluster
  metadata:
    name: my-cluster
  spec:
    hubAcceptsClient: true
  ```

2. Retrieve the import command and apply on the target cluster:

  ```bash
  oc get secret my-cluster-import -n my-cluster -o jsonpath='{.data.import\.yaml}' | base64 -d | oc apply -f - --kubeconfig={{ managed_cluster_kubeconfig }}
  ```
