# Validate the POC

This section contains workloads and operational tests that demonstrate OpenShift capabilities to stakeholders. Run these after completing the [cluster configuration](../configure-the-cluster/index.md).

## Container Workloads

Deploy sample applications to validate the platform's container orchestration, storage, networking, and build capabilities:

- [Overview](./container-workloads/index.md) — Summary of container workload types and deployment patterns
- [Hello World Web Server](./container-workloads/hello-world-web-server.md) — Minimal Nginx deployment to confirm basic pod scheduling and routing
- [Spring PetClinic](./container-workloads/spring-petclinic.md) — Multi-tier Java application with a PostgreSQL backend
- [Kafka (Strimzi)](./container-workloads/kafka-strimzi.md) — Event streaming platform to validate stateful workloads
- [Source-to-Image (S2I) Build](./container-workloads/s2i-build.md) — Build and deploy directly from source code
- [PostgreSQL with Persistent Storage](./container-workloads/postgresql.md) — Validate CSI storage with a stateful database
- [PVC Read-Back Test](./container-workloads/pvc-readback.md) — Write-then-read PVC test to confirm storage I/O
- [Bookinfo (Service Mesh)](./container-workloads/bookinfo.md) — Multi-service mesh demo (**only if Service Mesh is in scope**)

## Virtual Machine Workloads

- [Deploying Virtual Machines](./virtual-machine-workloads/index.md) — Create and manage VMs using OpenShift Virtualization

## Operational Validation

Demonstrate resilience, backup/restore, and failover capabilities:

- [VM Failover Test](./operational-validation/vm-failover.md) — Validate VM high availability with node drain and recovery
- [Container Failover Test](./operational-validation/container-failover.md) — Confirm pod rescheduling on node failure
- [VM Backup and Restore](./operational-validation/vm-backup-restore.md) — OADP-based backup and restore of virtual machines

## Day-2 Operations

Demonstrate cluster lifecycle management:

- [Day-2 Overview](./day-2-operations/index.md) — Summary of operational procedures
- [Add Worker Node](./day-2-operations/add-worker-node.md) — Expand cluster capacity with a new worker
- [Rotate SSH Keys](./day-2-operations/rotate-ssh-keys.md) — Replace SSH keys on all cluster nodes
- [Machine Config](./day-2-operations/machine-config.md) — Apply node-level configuration changes
- [Debugging MTU Mismatches](./day-2-operations/debug-mtu.md) — Diagnose network MTU issues
