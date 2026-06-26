# Advanced Cluster Management

Red Hat Advanced Cluster Management (ACM) provides multicluster lifecycle management, governance, and observability. Installing ACM also automatically installs the multicluster engine operator.

[Red Hat ACM Documentation](https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/latest)

!!! note
    Only one ACM hub cluster can exist per OpenShift cluster.

## Prerequisites

- Hub cluster is installed and storage is configured
- Cluster administrator privileges

## Install the Operator

```bash
cat <<EOF | oc apply -f -
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
EOF
```

Wait for the operator to install:

```bash
oc get csv -n open-cluster-management -w
```

The `PHASE` should show `Succeeded`.

## Create the MultiClusterHub

```bash
cat <<EOF | oc apply -f -
apiVersion: operator.open-cluster-management.io/v1
kind: MultiClusterHub
metadata:
  name: multiclusterhub
  namespace: open-cluster-management
spec: {}
EOF
```

!!! note
    It can take up to 10 minutes for the hub to finish deploying all components.

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

```bash
cat <<EOF | oc apply -f -
apiVersion: metal3.io/v1alpha1
kind: Provisioning
metadata:
  name: provisioning-configuration
spec:
  provisioningNetwork: "Disabled"
  watchAllNamespaces: true
EOF
```

## Create InfraEnv

```bash
cat <<EOF | oc apply -f -
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
  sshAuthorizedKey: <public-key>
EOF
```

## Adding Host Inventory via Redfish

Create the BMC secret:

```bash
oc create secret generic <hostname>-bmc-secret \
  --from-literal=username=admin \
  --from-literal=password=your-bmc-password \
  -n <InfraEnv-namespace>
```

Create the BareMetalHost:

```yaml
apiVersion: metal3.io/v1alpha1
kind: BareMetalHost
metadata:
  name: <hostname>-bmh
  namespace: <InfraEnv-namespace>
  labels:
    infraenvs.agent-install.openshift.io: <InfraEnv-namespace>
spec:
  bmc:
    address: redfish-virtualmedia://<bmc-ip>/redfish/v1/
    credentialsName: "<hostname>-bmc-secret"
    disableCertificateVerification: true
  bootMACAddress: "aa:bb:cc:dd:ee:ff"
  online: false
```

## Import a Managed Cluster

To import an existing cluster into ACM:

```bash
cat <<EOF | oc apply -f -
apiVersion: cluster.open-cluster-management.io/v1
kind: ManagedCluster
metadata:
  name: my-cluster
spec:
  hubAcceptsClient: true
EOF
```

Then retrieve the import command to run on the target cluster:

```bash
oc get secret my-cluster-import -n my-cluster -o jsonpath='{.data.import\.yaml}' | base64 -d | oc apply -f - --kubeconfig=<managed-cluster-kubeconfig>
```
