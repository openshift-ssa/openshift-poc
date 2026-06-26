# Workload Availability

[Workload Availability Documentation](https://docs.redhat.com/en/documentation/workload_availability_for_red_hat_openshift/latest)

Workload Availability involves a set of operators that work together to detect unhealthy nodes, remediate them automatically, and rebalance pod placement across the cluster.

| Operator                        | Purpose                                                                    |
| ------------------------------- | -------------------------------------------------------------------------- |
| Node Health Check Operator      | Monitors node conditions and triggers remediation when a node is unhealthy |
| Self Node Remediation Operator  | Reboots unhealthy nodes automatically                                      |
| Kube Descheduler Operator       | Evicts pods so the scheduler can rebalance them across nodes               |

## Self Node Remediation Operator

Runs on every node as a DaemonSet and reboots nodes identified as unhealthy. It minimizes downtime for stateful applications and RWO volumes. Works regardless of the management interface (IPMI, BMC) or cluster installation type.

The operator determines its remediation strategy based on available watchdog devices:

1. Hardware watchdog device (most reliable)
2. Software watchdog (`softdog`)
3. Software reboot (fallback)

## Node Health Check Operator

Monitors node conditions and creates remediation requests when nodes become unhealthy. Automatically installs the Self Node Remediation Operator as the default remediation provider.

### Install

```bash
cat <<EOF | oc apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-workload-availability
---
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: workload-availability-operator-group
  namespace: openshift-workload-availability
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: node-health-check-operator
  namespace: openshift-workload-availability
spec:
  channel: stable
  installPlanApproval: Automatic
  name: node-health-check-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
EOF
```

### Configure NodeHealthCheck

!!! note
    Do not select both worker and control-plane nodes in the same `NodeHealthCheck` CR. Create separate CRs for each group.

```yaml
apiVersion: remediation.medik8s.io/v1alpha1
kind: NodeHealthCheck
metadata:
  name: nhc-worker
spec:
  selector:
    matchExpressions:
      - key: node-role.kubernetes.io/worker
        operator: Exists
  minHealthy: 51%
  unhealthyConditions:
    - type: Ready
      status: "False"
      duration: 300s
    - type: Ready
      status: Unknown
      duration: 300s
  remediationTemplate:
    apiVersion: self-node-remediation.medik8s.io/v1alpha1
    kind: SelfNodeRemediationTemplate
    name: self-node-remediation-automatic-strategy-template
    namespace: openshift-workload-availability
```

## Kube Descheduler Operator

Runs periodically and evicts pods that violate scheduling rules so the default scheduler can reschedule them onto more appropriate nodes.

!!! note
    The descheduler does not schedule pods — it only evicts. The default scheduler then places them on better-fit nodes.

### Install

```bash
cat <<EOF | oc apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-kube-descheduler-operator
---
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: openshift-kube-descheduler-operator
  namespace: openshift-kube-descheduler-operator
spec:
  targetNamespaces:
    - openshift-kube-descheduler-operator
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: cluster-kube-descheduler-operator
  namespace: openshift-kube-descheduler-operator
spec:
  channel: stable
  installPlanApproval: Automatic
  name: cluster-kube-descheduler-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
EOF
```

### Configure

Only one `KubeDescheduler` is allowed per cluster and it must be named `cluster`:

```yaml
apiVersion: operator.openshift.io/v1
kind: KubeDescheduler
metadata:
  name: cluster
  namespace: openshift-kube-descheduler-operator
spec:
  deschedulingIntervalSeconds: 3600
  profiles:
    - AffinityAndTaints
    - LifecycleAndUtilization
  mode: Predictive
```

### Descheduler Profiles

| Profile                     | Description                                                           |
| --------------------------- | --------------------------------------------------------------------- |
| `AffinityAndTaints`         | Evicts pods violating anti-affinity, node affinity, and taint rules   |
| `TopologyAndDuplicates`     | Balances topology domain constraints and spreads duplicates           |
| `LifecycleAndUtilization`   | Evicts from overutilized nodes and long-running pods to rebalance     |
| `DevPreviewLongLifecycle`   | Targets long-running pods; use for OpenShift Virtualization           |

### Modes

- **Predictive** — Simulates evictions and reports what would be evicted (dry-run)
- **Automatic** — Actively evicts pods based on configured profiles
