# Advanced Cluster Management

After installing the SNO hub cluster, install Red Hat Advanced Cluster Management for Kubernetes (ACM) to enable fleet management capabilities.

## Steps

1. Install the ACM operator
2. Create the MultiClusterHub resource
3. Wait for ACM to become available
4. Access the ACM console

```bash
export KUBECONFIG=~/hub-cluster/auth/kubeconfig

oc apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  name: open-cluster-management
  labels:
    openshift.io/cluster-monitoring: "true"
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
  name: advanced-cluster-management
  namespace: open-cluster-management
spec:
  channel: release-2.12
  installPlanApproval: Automatic
  name: advanced-cluster-management
  source: redhat-operators
  sourceNamespace: openshift-marketplace
EOF
```

Wait for the operator to install:

```bash
oc get csv -n open-cluster-management -w
```

Create the MultiClusterHub:

```bash
oc apply -f - <<EOF
apiVersion: operator.open-cluster-management.io/v1
kind: MultiClusterHub
metadata:
  name: multiclusterhub
  namespace: open-cluster-management
spec: {}
EOF
```

Wait for ACM to be ready:

```bash
oc get multiclusterhub -n open-cluster-management -w
```

Access the ACM console:

```bash
oc get route multicloud-console -n open-cluster-management -o jsonpath='{.spec.host}'
```

---

## Details

### What ACM Provides

| Capability               | Description                                                    |
| ------------------------ | -------------------------------------------------------------- |
| Cluster lifecycle        | Create, import, upgrade, and destroy clusters                  |
| Governance               | Apply policies and enforce compliance across the fleet         |
| Application management   | Deploy applications across multiple clusters                   |
| Observability            | Centralized monitoring and alerting for all clusters           |
| Infrastructure provisioning | Provision clusters on bare metal, vSphere, and cloud       |

### Provisioning Spoke Clusters

Once ACM is running, you can provision additional clusters from the hub using:

- **Central Infrastructure Management (CIM)** — bare metal provisioning integrated with the Assisted Installer
- **Hosted Control Planes** — lightweight clusters with control planes running on the hub
- **Hive** — full cluster provisioning on supported platforms

### Importing Existing Clusters

If you already have clusters running, you can import them into ACM for centralized management:

```bash
# Generate the import command from the ACM console, or:
oc apply -f - <<EOF
apiVersion: cluster.open-cluster-management.io/v1
kind: ManagedCluster
metadata:
  name: spoke-cluster-1
spec:
  hubAcceptsClient: true
EOF
```

### Next Steps After ACM Installation

1. Configure identity provider on the hub (see [Day 2 Operations](../post-installation/day2.md))
2. Set up OpenShift GitOps for fleet-wide configuration
3. Define governance policies for the fleet
4. Provision spoke clusters for development, test, and production workloads
