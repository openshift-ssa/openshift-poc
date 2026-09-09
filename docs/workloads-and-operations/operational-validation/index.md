# Operational Validation

These exercises prove that the cluster can recover from failures and protect data — two of the most important POC outcomes. Run them after you have deployed workloads from the [Container Workloads](../container-workloads/index.md) and [Virtual Machine Workloads](../virtual-machine-workloads/index.md) sections.

| Test | What It Proves | Prerequisites |
|------|---------------|---------------|
| [VM Failover Test](./vm-failover.md) | Node-loss recovery within 120 seconds for VMs | [Workload Availability](../../configure-the-cluster/workload-availability.md), [Virtualization](../../configure-the-cluster/virtualization.md), RWX storage |
| [Container Failover Test](./container-failover.md) | Container rescheduling on node failure | [Workload Availability](../../configure-the-cluster/workload-availability.md) |
| [VM Backup and Restore](./vm-backup-restore.md) | OADP can back up a running VM and restore it after deletion | [OADP](../../configure-the-cluster/oadp.md), [Virtualization](../../configure-the-cluster/virtualization.md) |

!!! tip
    These tests are designed to be run in front of stakeholders — they produce clear, demonstrable results (VM comes back on a different node, data is restored after deletion). Schedule them for the POC review day.
