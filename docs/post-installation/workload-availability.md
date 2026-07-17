# Workload Availability

[Workload Availability Documentation](https://docs.redhat.com/en/documentation/workload_availability_for_red_hat_openshift/latest)

Workload Availability involves a set of operators that work together to detect unhealthy nodes, remediate them automatically, and rebalance pod and virtual machine placement across the cluster.

| Operator                       | Purpose                                                                    |
| ------------------------------ | -------------------------------------------------------------------------- |
| Node Health Check Operator     | Monitors node conditions and triggers remediation when a node is unhealthy |
| Self Node Remediation Operator | Reboots unhealthy nodes automatically                                      |
| Kube Descheduler Operator      | Evicts pods so the scheduler can rebalance them across nodes               |
| Node Maintenance Operator      | Cordons and drains nodes for planned maintenance                           |

## Flow of Events

When a node becomes unhealthy, the following phases occur:

1. **Kubernetes Health Check** — After ~50 seconds without communication, the API server sets the node's Ready condition to `Unknown`
2. **Node Health Check** — If the unhealthy condition persists longer than the configured duration, NHC creates a remediation CR
3. **Remediation** — The configured remediator (Self Node Remediation by default) fences and reboots the node
4. **Workload Restart** — Resources are deleted and workloads are rescheduled to healthy nodes

!!! info "VM Failover Target: 120 seconds"
    The target for virtual machine failover is 120 seconds from node failure to VM restart on a healthy node. To achieve this, the `unhealthyConditions` duration should be set low enough to account for the ~50 second Kubernetes detection phase plus the remediation and rescheduling time.

## Self Node Remediation Operator

Runs on every node as a DaemonSet and reboots nodes identified as unhealthy. It minimizes downtime for stateful applications and RWO volumes. Works regardless of the management interface (IPMI, BMC) or cluster installation type.

The operator determines its remediation strategy based on available watchdog devices:

1. Hardware watchdog device (most reliable)
2. Software watchdog (`softdog`)
3. Software reboot (fallback)

### Control Plane Fencing

Self Node Remediation now supports control plane nodes in addition to worker nodes. When a control plane node loses API server connectivity, the operator:

1. Checks the status with the majority of peer worker nodes
2. If the majority of peers cannot be reached, performs self-diagnostics (kubelet status, endpoint availability)
3. If self-diagnostics fail, the node is fenced and remediated

!!! warning
    The Node Health Check Operator enforces a maximum of one control plane node being remediated at a time.

## Node Health Check Operator

Monitors node conditions and creates remediation requests when nodes become unhealthy. Automatically installs the Self Node Remediation Operator as the default remediation provider.

### Install via WebUI

1. Go to Ecosystem -> Software Catalog -> filter for "Node Health Check" -> click the tile
2. Click Install
3. Leave all the defaults (installs to `openshift-workload-availability` namespace) and click Install
4. Wait for the Operator to install — it will also install the Self Node Remediation Operator automatically

### Install via YAML

```yaml
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
```

```bash
oc apply -f nhc-operator.yaml
```

### Configure NodeHealthCheck for Workers

!!! warning "Separate CRs Required"
    Do not select both worker and control-plane nodes in the same `NodeHealthCheck` CR. Create separate CRs for each group. Grouping them together results in incorrect evaluation of the minimum healthy node count and can cause unexpected or missing remediations.

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
  stormCooldownDuration: 60s
  unhealthyConditions:
    - type: Ready
      status: "False"
      duration: 30s
    - type: Ready
      status: Unknown
      duration: 30s
  remediationTemplate:
    apiVersion: self-node-remediation.medik8s.io/v1alpha1
    kind: SelfNodeRemediationTemplate
    name: self-node-remediation-automatic-strategy-template
    namespace: openshift-workload-availability
```

!!! tip "120-Second Failover"
    With a 30s duration threshold, the total timeline is approximately: 50s (Kubernetes detection) + 30s (NHC threshold) + ~40s (remediation and VM restart) = ~120s total failover time.

### Configure NodeHealthCheck for Control Plane

```yaml
apiVersion: remediation.medik8s.io/v1alpha1
kind: NodeHealthCheck
metadata:
  name: nhc-control-plane
spec:
  selector:
    matchExpressions:
      - key: node-role.kubernetes.io/master
        operator: Exists
  minHealthy: 51%
  stormCooldownDuration: 60s
  unhealthyConditions:
    - type: Ready
      status: "False"
      duration: 30s
    - type: Ready
      status: Unknown
      duration: 30s
  remediationTemplate:
    apiVersion: self-node-remediation.medik8s.io/v1alpha1
    kind: SelfNodeRemediationTemplate
    name: self-node-remediation-automatic-strategy-template
    namespace: openshift-workload-availability
```

### Escalating Remediations

You can configure multiple remediation strategies that escalate if the initial remediation does not succeed within a timeout:

```yaml
apiVersion: remediation.medik8s.io/v1alpha1
kind: NodeHealthCheck
metadata:
  name: nhc-worker-escalating
spec:
  selector:
    matchExpressions:
      - key: node-role.kubernetes.io/worker
        operator: Exists
  minHealthy: 51%
  escalatingRemediations:
    - remediationTemplate:
        apiVersion: self-node-remediation.medik8s.io/v1alpha1
        name: self-node-remediation-resource-deletion-template
        namespace: openshift-workload-availability
        kind: SelfNodeRemediationTemplate
      order: 1
      timeout: 120s
  unhealthyConditions:
    - type: Ready
      status: "False"
      duration: 30s
    - type: Ready
      status: Unknown
      duration: 30s
```

### Pausing Remediation

Use `pauseRequests` to temporarily pause remediation during planned maintenance:

```yaml
spec:
  pauseRequests:
    - "planned-maintenance-window"
```

Remove the pause request entry to resume remediation.

### Key Configuration Fields

| Field                    | Description                                                                    |
| ------------------------ | ------------------------------------------------------------------------------ |
| `minHealthy`             | Minimum percentage/number of healthy nodes required before remediation triggers |
| `maxUnhealthy`           | Alternative to minHealthy — max unhealthy nodes allowed                        |
| `stormCooldownDuration`  | Cooldown period after a storm of remediations (default 60s)                    |
| `pauseRequests`          | List of strings to pause remediation during maintenance                        |
| `escalatingRemediations` | Ordered list of remediation strategies with timeouts                           |

### Verify

```bash
oc get nodehealthcheck -A
oc get selfnoderemediationtemplate -n openshift-workload-availability
oc get daemonset -n openshift-workload-availability
```

## Kube Descheduler Operator

Runs periodically and evicts pods that violate scheduling rules so the default scheduler can reschedule them onto more appropriate nodes.

!!! note
    The descheduler does not schedule pods — it only evicts. The default scheduler then places them on better-fit nodes.

### Install via WebUI

1. Go to Ecosystem -> Software Catalog -> filter for "Kube Descheduler" -> click the tile
2. Click Install
3. Leave all the defaults and click Install
4. Wait for the Operator to install

### Install via YAML

```yaml
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
```

```bash
oc apply -f descheduler-operator.yaml
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

| Profile                   | Description                                                         |
| ------------------------- | ------------------------------------------------------------------- |
| `AffinityAndTaints`       | Evicts pods violating anti-affinity, node affinity, and taint rules |
| `TopologyAndDuplicates`   | Balances topology domain constraints and spreads duplicates         |
| `LifecycleAndUtilization` | Evicts from overutilized nodes and long-running pods to rebalance   |
| `DevPreviewLongLifecycle` | Targets long-running pods; use for OpenShift Virtualization         |

### Modes

- **Predictive** — Simulates evictions and reports what would be evicted (dry-run)
- **Automatic** — Actively evicts pods based on configured profiles

## VM Failover: Sequence of Events

The following describes the complete sequence when a node running a virtual machine fails unexpectedly (e.g., power loss, kernel panic, network partition):

### Timeline

| Time    | Event                                                                                         |
| ------- | --------------------------------------------------------------------------------------------- |
| T+0s    | Node fails — stops responding to the API server                                               |
| T+~50s  | API server marks node condition `Ready=Unknown` after missing heartbeats                      |
| T+~80s  | NHC detects the unhealthy condition has exceeded the 30s `duration` threshold                 |
| T+~80s  | NHC creates a `SelfNodeRemediation` CR for the unhealthy node                                |
| T+~85s  | SNR marks the node as unschedulable and applies the `OutOfServiceTaint`                       |
| T+~90s  | The `OutOfServiceTaint` allows Kubernetes to force-delete pods and VolumeAttachments on the node |
| T+~95s  | The VM pod is deleted and the `VirtualMachineInstance` is rescheduled by the virt-controller  |
| T+~100s | The VM pod starts on a healthy node, attaches RWX storage                                    |
| T+~120s | The VM is fully running on the new node                                                      |

### What Happens Under the Hood

1. **Node goes silent** — The kubelet stops sending heartbeats. The node controller in the API server waits for the `node-monitor-grace-period` (default 40s) before marking the node `Unknown`.

2. **NHC evaluates conditions** — The Node Health Check controller observes the `Ready=Unknown` condition and starts counting against the configured `duration` (30s in our configuration).

3. **Remediation CR created** — Once the threshold is breached, NHC creates a `SelfNodeRemediation` CR. The `minHealthy` check ensures remediation only proceeds if enough healthy nodes remain.

4. **Self Node Remediation acts** — SNR applies the `out-of-service` taint (`node.kubernetes.io/out-of-service:NoExecute`) which signals the cluster that the node is definitively unreachable. This taint allows the `attach-detach-controller` to force-detach volumes without waiting for the node to confirm.

5. **Volume and pod cleanup** — Kubernetes deletes the `VolumeAttachment` resources and the pods on the failed node. For VMs using RWX PVCs, this allows the volumes to be mounted on another node immediately.

6. **VM rescheduling** — The `virt-controller` detects the `VirtualMachineInstance` is gone and, if the `VirtualMachine` has `spec.runStrategy: Always` or `spec.running: true`, creates a new `VirtualMachineInstance` on a healthy node.

7. **VM starts on new node** — The new pod starts, storage is attached, and the VM boots. The guest OS starts fresh (this is not a live migration — it is a cold restart).

!!! warning "RWX Storage Required"
    VM failover requires RWX (ReadWriteMany) storage for the VM disks. With RWO (ReadWriteOnce) volumes, the volume cannot be attached to a new node until it is fully detached from the failed node, which can take 6+ minutes waiting for the node lease to expire.

!!! note "Not a Live Migration"
    This is a failover, not a live migration. The VM is stopped on the failed node and cold-started on a new node. Any in-memory state is lost. Applications inside the VM should be designed to handle unexpected restarts.

## Achieving Sub-120-Second Failover

Reducing the failover time below 120 seconds (e.g., to 30 seconds) is theoretically possible but introduces significant complexity, risk, and testing requirements.

### Tunable Parameters

| Parameter                          | Default   | Aggressive | Where                              |
| ---------------------------------- | --------- | ---------- | ---------------------------------- |
| `node-monitor-grace-period`        | 40s       | 10s        | kube-controller-manager            |
| NHC `unhealthyConditions.duration` | 30s       | 5s         | NodeHealthCheck CR                 |
| SNR `safeTimeToAssumeNodeRebootedSeconds` | 180s | 30s  | SelfNodeRemediationConfig CR       |
| kubelet `nodeStatusUpdateFrequency` | 10s      | 5s         | KubeletConfig CR                   |

### Complications

**False positives** — Lowering the `node-monitor-grace-period` and NHC duration means that transient network blips, brief CPU starvation, or garbage collection pauses can trigger unnecessary remediations. A node that would have recovered in 15 seconds may instead be rebooted, causing more disruption than the original issue.

**Control plane load** — More frequent kubelet heartbeats (`nodeStatusUpdateFrequency`) increase API server load. On large clusters, this compounds quickly.

**etcd impact** — Every heartbeat update writes to etcd. Reducing the interval from 10s to 5s doubles the write load for node status alone.

**Split-brain risk** — With very short detection windows, a network partition between the node and the API server (but not the node and storage) can result in the same VM starting on two nodes simultaneously if the fencing is not reliable.

**Watchdog dependency** — For sub-30-second failover, a hardware watchdog device is effectively mandatory. Software watchdog and software reboot strategies add unpredictable delays.

**Storage detach timing** — Even with the `OutOfServiceTaint`, the storage subsystem has its own detach/attach cycle. Some CSI drivers add their own timeouts or require confirmation before allowing re-attachment.

### Testing Requirements

Before deploying aggressive thresholds in production:

1. **Simulate node failures** — Use `systemctl stop kubelet` and `ip link set down` to simulate various failure modes and measure actual failover times
2. **Test under load** — Run the cluster at realistic utilization levels during failure testing; idle clusters mask timing issues
3. **Test network partitions** — Verify behavior when a node loses API server connectivity but not storage connectivity
4. **Validate watchdog** — Confirm hardware watchdog devices are present and functional on all nodes (`ls /dev/watchdog*`)
5. **Measure false positive rate** — Run for at least a week at aggressive thresholds and monitor for unnecessary remediations
6. **Verify storage behavior** — Confirm your CSI driver supports force-detach and measure its attach/detach cycle time
7. **Document accepted risk** — Aggressive thresholds trade stability for speed; ensure stakeholders understand the trade-offs

!!! danger "Recommendation"
    Start with the 120-second configuration documented above. Only pursue lower thresholds after validating the 120-second target works reliably in your environment. Reduce one parameter at a time and test thoroughly between changes.

## Node Maintenance Operator

[Node Maintenance Operator Documentation](https://docs.redhat.com/en/documentation/workload_availability_for_red_hat_openshift/latest/html/remediation_fencing_and_maintenance/node-maintenance-operator)

The Node Maintenance Operator provides a declarative way to place nodes into maintenance mode. When a `NodeMaintenance` custom resource is created, the operator cordons the node and drains evictable pods (including virtual machines). Deleting the CR resumes the node and makes it schedulable again.

This achieves the same result as `oc adm cordon` and `oc adm drain`, but through standard OpenShift custom resource processing.

### Install via WebUI

1. Go to Ecosystem -> Software Catalog -> filter for "Node Maintenance" -> click the tile
2. Click Install
3. Install into the `openshift-workload-availability` namespace (create it if it does not already exist)
4. Leave the remaining defaults and click Install
5. Wait for the Operator to install

### Install via YAML

```yaml
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
  name: node-maintenance-operator
  namespace: openshift-workload-availability
spec:
  channel: stable
  installPlanApproval: Automatic
  name: node-maintenance-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
```

```bash
oc apply -f node-maintenance-operator.yaml
```

Wait for the operator to install:

```bash
oc get csv -n openshift-workload-availability -w
```

### Place a Node in Maintenance Mode

```yaml
apiVersion: nodemaintenance.medik8s.io/v1beta1
kind: NodeMaintenance
metadata:
  name: node-maintenance-example
spec:
  nodeName: {{ node_name }}
  reason: Scheduled maintenance
```

```bash
oc apply -f node-maintenance.yaml
```

Check status:

```bash
oc get nodemaintenance
oc describe nodemaintenance node-maintenance-example
```

### Resume a Node from Maintenance Mode

Delete the `NodeMaintenance` CR to uncordon the node and allow workloads to schedule again:

```bash
oc delete nodemaintenance node-maintenance-example
```

