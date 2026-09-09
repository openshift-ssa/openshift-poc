# Cluster Upgrade

[Red Hat OpenShift Update Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/updating_clusters/index)

This procedure walks through upgrading an OpenShift cluster to a new z-stream (e.g., 4.22.10 → 4.22.11) or minor version (e.g., 4.22 → 4.23). Validating a cluster upgrade is a key POC milestone — it proves the cluster can be maintained without downtime.

## Prerequisites

- Cluster administrator privileges
- Cluster health verified (all ClusterOperators available, no degraded conditions)
- If disconnected: the target release image must be mirrored — see [Disconnected](../../install-the-cluster/other-installation-methods/disconnected.md)
- Workloads with proper `PodDisruptionBudgets` for zero-downtime validation

## Pre-Upgrade Health Check

Before starting, confirm the cluster is healthy:

```bash
oc get clusterversion
oc get co | grep -v "True.*False.*False"
oc get nodes
oc get mcp
```

All ClusterOperators should show `AVAILABLE=True`, `PROGRESSING=False`, `DEGRADED=False`. All nodes should be `Ready`. All MachineConfigPools should show `UPDATED=True`.

!!! warning "Do Not Upgrade a Degraded Cluster"
    Resolve any degraded ClusterOperators or unhealthy nodes before starting an upgrade. Upgrading a degraded cluster can make conditions worse and harder to troubleshoot.

## Check Available Updates

### Via CLI

```bash
oc adm upgrade
```

This shows the current version and lists available update targets. For z-stream updates, you will see patch versions in the same minor release. For minor version updates, you may need to update the channel first.

### Via WebUI

1. Go to **Administration** → **Cluster Settings**
2. The **Update** section shows the current version and available updates

## Change the Update Channel (Minor Version Upgrades Only)

To upgrade to a new minor version (e.g., 4.22 → 4.23), you must first switch the update channel:

```bash
oc adm upgrade channel stable-4.23
```

Then check available updates again:

```bash
oc adm upgrade
```

!!! note
    For z-stream updates within the same minor version, the channel does not need to change.

## Start the Upgrade

### Via CLI

For z-stream updates, pick a version from the available updates list:

```bash
oc adm upgrade --to={{ target_version }}
```

For the latest available z-stream:

```bash
oc adm upgrade --to-latest
```

### Via WebUI

1. Go to **Administration** → **Cluster Settings**
2. Click **Update** next to the desired version
3. Confirm the update

## Monitor the Upgrade

### Watch ClusterVersion Progress

```bash
oc get clusterversion -w
```

The `PROGRESSING` column shows the update status. The update is complete when `PROGRESSING=False` and `VERSION` shows the target version.

### Watch ClusterOperator Rollouts

```bash
watch "oc get co | head -1; oc get co | grep -E 'True.*True|False'"
```

This highlights any operator that is still progressing or has become unavailable during the update.

### Watch Node Updates

Nodes are updated via the Machine Config Operator, which reboots them serially:

```bash
oc get nodes -w
```

```bash
oc get mcp -w
```

Nodes will cycle through `Ready` → `NotReady,SchedulingDisabled` → `Ready` as they are cordoned, drained, rebooted with the new OS image, and uncordoned.

!!! tip
    A typical 6-node cluster (3 control plane + 3 worker) takes 45–90 minutes for a z-stream update, depending on workload drain times and node reboot speed.

## Validate Workloads During Upgrade

While the upgrade is in progress, verify that workloads remain available:

```bash
oc get pods -A | grep -v Running | grep -v Completed
```

If you deployed workloads from the [Container Workloads](../container-workloads/index.md) or [Virtual Machine Workloads](../virtual-machine-workloads/index.md) sections, confirm they are still serving traffic:

```bash
curl -sk https://$(oc get route hello-world -n hello-world -o jsonpath='{.spec.host}')
```

VMs with `evictionStrategy: LiveMigrate` will live-migrate off nodes before they are rebooted. Watch for migration events:

```bash
oc get vmi -A -w
```

## Post-Upgrade Verification

Once the upgrade completes:

1. Confirm the new version:

  ```bash
  oc get clusterversion
  ```

2. Verify all ClusterOperators are healthy:

  ```bash
  oc get co
  ```

3. Verify all nodes are Ready and running the new version:

  ```bash
  oc get nodes -o wide
  ```

4. Verify MachineConfigPools are updated:

  ```bash
  oc get mcp
  ```

5. Check for any alerts:

  ```bash
  oc get prometheusrule -A 2>/dev/null
  oc adm top nodes
  ```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Upgrade stalls at a percentage | A ClusterOperator is waiting for a resource | Check `oc get co` for operators showing `PROGRESSING=True` and inspect their logs |
| Node stuck in `NotReady` after reboot | Node failed to come back cleanly | Check BMC console; may need manual reboot. Check `oc get mcp` for degraded status |
| Pods stuck in `Terminating` during drain | PodDisruptionBudget blocking eviction | Check `oc get pdb -A`; temporarily relax the PDB if safe |
| `oc adm upgrade` shows no updates | Wrong channel or disconnected without mirror | Verify channel: `oc get clusterversion -o jsonpath='{.spec.channel}'`; check mirror if disconnected |

## Rollback

OpenShift does not support downgrading to a previous minor version. Z-stream rollback is also not supported. If an upgrade fails partway:

1. Check `oc get clusterversion -o yaml` for detailed status conditions
2. Run `oc adm must-gather` to collect diagnostics — see [must-gather](./must-gather.md)
3. Open a Red Hat support case with the must-gather output
