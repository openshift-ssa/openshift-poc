# POC Checklist

This checklist provides a complete end-to-end baseline for validating OpenShift in your environment. It covers discovery, infrastructure preparation, installation, configuration, VM migration, workload deployment, operational validation, and formal closure.

Use this as a tracker for your POC engagement. Not every item will apply to every environment — skip sections that are out of scope for your specific goals.

---

## Phase 1: Discovery and Scoping

Complete this phase before any technical work begins. Align on goals, boundaries, and what a successful outcome looks like.

### Goals and Drivers

- [ ] Define the core business problem OpenShift will address
- [ ] Document specific POC objectives with measurable outcomes
- [ ] Identify which applications or workloads will be evaluated
- [ ] Capture high-availability and recovery expectations
- [ ] Note any security, regulatory, or compliance constraints
- [ ] Understand target production timeline and anticipated scale

### Boundaries and Assumptions

- [ ] Agree on what is included in the POC and document it
- [ ] Explicitly list what is excluded (to prevent scope creep)
- [ ] Document assumptions and responsibilities (customer vs. Red Hat)
- [ ] Identify all participating teams (infra, network, security, app dev)
- [ ] Set a timeline with key milestone dates

### Exit Criteria

Agree on pass/fail criteria before installation begins:

| Area           | How We Measure Success                            | Status |
| -------------- | ------------------------------------------------- | ------ |
| Installation   | Cluster deployed, all nodes healthy               |        |
| Networking     | Application traffic flows end-to-end              |        |
| Storage        | Persistent volumes provision and bind on demand   |        |
| Security       | Users authenticate and RBAC enforces permissions  |        |
| Applications   | Sample and customer workloads run correctly       |        |
| Performance    | Workloads meet agreed throughput/latency targets  |        |
| Resilience     | Cluster recovers from simulated failures          |        |
| Operations     | Monitoring, logging, and backups function         |        |
| Migration      | VMs move from VMware to OpenShift (if applicable) |        |

---

## Phase 2: Prerequisites

Complete these before scheduling the installation.

- [ ] Red Hat account created and trial subscriptions allocated
- [ ] Infrastructure provisioned ([details](infrastructure.md))
    - [ ] Compute nodes meet minimum specs (control plane + workers)
    - [ ] BMC/iLO/iDRAC access confirmed for bare metal
    - [ ] BIOS/firmware settings validated (UEFI, virtualization extensions)
- [ ] Networking configured ([details](networking.md))
    - [ ] VLANs/subnets allocated for cluster traffic
    - [ ] Firewall rules opened (API, ingress, registry access)
    - [ ] NTP accessible from all nodes
    - [ ] Load balancer configured (if required)
- [ ] DNS records created ([details](dns.md))
    - [ ] `api.<cluster>.<domain>` resolves correctly
    - [ ] `*.apps.<cluster>.<domain>` wildcard resolves correctly
    - [ ] Reverse DNS entries (PTR) configured
- [ ] Storage backend available ([details](storage.md))
    - [ ] SAN/NAS or local storage provisioned
    - [ ] iSCSI/NFS/FC connectivity verified from node networks
- [ ] Installation host prepared ([details](installation-host.md))
    - [ ] `oc` CLI installed
    - [ ] Pull secret downloaded from Red Hat console
    - [ ] SSH key pair generated

---

## Phase 3: Installation

- [ ] Installation method chosen:
    - [ ] [Assisted Installer](../installation/assisted-installer.md) (recommended for connected environments)
    - [ ] [Agent-Based Installer](../installation/agent-based.md) (disconnected or air-gapped)
    - [ ] [VMware vSphere IPI](../installation/vmware-install.md) (vSphere environments)
- [ ] Cluster installation completed successfully
- [ ] All nodes showing `Ready` status (`oc get nodes`)
- [ ] All ClusterOperators report Available=True, Degraded=False (`oc get co`)
- [ ] Cluster version matches target release (`oc get clusterversion`)
- [ ] Web console accessible at `https://console-openshift-console.apps.<cluster>.<domain>`
- [ ] `kubeadmin` credentials stored securely

---

## Phase 4: Post-Installation (Required)

These must be completed before deploying workloads.

- [ ] [NMState Operator](../post-installation/nmstate.md) installed (if using bonds, VLANs, or OVS bridges)
- [ ] Storage driver installed and StorageClasses created ([Storage](../post-installation/storage/index.md))
    - [ ] Default StorageClass set
    - [ ] RWO PVC created and bound successfully
    - [ ] RWX PVC created and bound successfully (if applicable)
- [ ] [Image Registry](../post-installation/registry.md) configured with persistent storage

---

## Phase 5: Post-Installation (Optional)

Install based on your POC goals. Each subsection is independent.

### Networking

- [ ] [Networking](../post-installation/networking.md) — NNCPs, OVS bridges, secondary networks configured
- [ ] Pod-to-pod communication verified across nodes
- [ ] Ingress/Route exposes an application externally
- [ ] DNS resolution works from within pods (internal and external)

### Virtualization

- [ ] [OpenShift Virtualization](../post-installation/virtualization.md) installed
    - [ ] HyperConverged CR created
    - [ ] Live migration network configured (if applicable)
- [ ] [Workload Availability](../post-installation/workload-availability.md) configured
    - [ ] Node Health Check Operator installed
    - [ ] Self Node Remediation Operator installed
    - [ ] NodeHealthCheck CRs created (workers and control plane)
    - [ ] Kube Descheduler Operator installed and configured

### Migration

- [ ] [Migration Toolkit for Virtualization](../post-installation/mtv.md) installed
    - [ ] VMware vSphere provider added
    - [ ] Network and storage mappings configured

### Backup and Restore

- [ ] [OADP](../post-installation/oadp.md) installed
    - [ ] Backup storage location configured (S3/MinIO)
    - [ ] DataProtectionApplication CR created

### Observability

- [ ] [Logging](../post-installation/logging.md) — Loki + ClusterLogForwarder configured
- [ ] [Network Observability](../post-installation/network-observability.md) — eBPF flow collection enabled
- [ ] [MultiCluster Observability](../post-installation/multicluster-observability.md) (if using ACM)

### Developer Experience

- [ ] [Service Mesh](../post-installation/service-mesh.md) — Istio ambient mode configured
- [ ] [OpenShift GitOps](../post-installation/openshift-gitops.md) — ArgoCD installed
- [ ] [Web Terminal](../post-installation/web-terminal.md) — Embedded CLI enabled
- [ ] [External Secrets Operator](../post-installation/external-secrets-operator.md) — Vault/secret integration

### Security and Access

- [ ] [Identity Providers](../post-installation/configuring-identity-providers.md) configured (LDAP, OIDC, etc.)
- [ ] RBAC groups mapped correctly (LDAP/OIDC group members get expected roles)
- [ ] `kubeadmin` secret removed after OAuth verification (if desired)
- [ ] [POC Banner](../post-installation/poc-banner.md) applied to mark environment as non-production

---

## Phase 6: VM Migration from VMware

Validate that virtual machines can be migrated from VMware vSphere to OpenShift Virtualization. Requires [MTV](../post-installation/mtv.md) and [OpenShift Virtualization](../post-installation/virtualization.md) from Phase 5.

- [ ] Source VMware environment accessible from OpenShift
- [ ] MTV provider connection healthy (green status in console)
- [ ] Migration plan created
    - [ ] Target storage class selected
    - [ ] Target network mapping configured
    - [ ] VMs selected for migration
- [ ] Test migration executed (cold migration)
    - [ ] VM boots successfully on OpenShift
    - [ ] Networking functional (IP, DNS, connectivity)
    - [ ] Storage attached and data intact
    - [ ] Applications inside the VM running correctly
- [ ] Warm migration tested (if applicable)
    - [ ] Cutover completed with minimal downtime
- [ ] Post-migration validation
    - [ ] VM accessible via console and SSH
    - [ ] Performance acceptable (CPU, memory, disk I/O)

---

## Phase 7: Workloads

Deploy workloads to validate platform capabilities.

### Container Workloads

- [ ] Basic container deployment ([Hello World](../workloads/busybox-hello-world.md))
    - [ ] Pod running and accessible via Route
- [ ] Source-to-Image build ([S2I Build](../workloads/s2i-build.md))
    - [ ] Build completes from source repository
    - [ ] Application deployed and accessible
- [ ] Stateful application ([PostgreSQL](../workloads/postgresql.md))
    - [ ] PVC bound and data persists across pod restarts
- [ ] Multi-tier application ([Spring PetClinic](../workloads/spring-petclinic.md))
    - [ ] Frontend and backend components communicating
- [ ] Event streaming ([Kafka](../workloads/kafka-strimzi.md)) (if applicable)
- [ ] Service mesh application ([Bookinfo](../workloads/bookinfo.md)) (if Service Mesh installed)
- [ ] Customer application deployed (if provided)

### Virtual Machine Workloads

- [ ] [Deploy a RHEL VM](../workloads/workload-virtual-machines.md) from template
    - [ ] VM boots and is accessible via console
    - [ ] SSH access functional
    - [ ] Storage attached correctly
- [ ] Live migration tested (move VM between nodes without downtime)
- [ ] Snapshot and restore tested

---

## Phase 8: Operational Validation

Demonstrate Day 2 operations and resilience.

### Failover and Resilience

- [ ] [VM Failover Test](../operations/vm-failover.md)
    - [ ] Node failure simulated
    - [ ] VM restarted on healthy node within target time (~120s)
    - [ ] Application recovered without manual intervention
- [ ] [Container Failover Test](../operations/container-failover.md)
    - [ ] Pod rescheduled to healthy node after node failure
    - [ ] Service remained available during failover

### Backup and Restore

- [ ] [VM Backup and Restore](../operations/vm-backup-restore.md)
    - [ ] Backup completed successfully
    - [ ] Restore to same or different namespace validated
    - [ ] Data integrity confirmed after restore
- [ ] etcd backup taken and verified
    - [ ] Backup script executed successfully
    - [ ] Backup file stored securely off-cluster

### Scaling

- [ ] [Add Worker Node](../operations/add-worker-node.md) — Scale cluster by adding a node
- [ ] Horizontal Pod Autoscaler (HPA) validated (if applicable)
    - [ ] Application scales under load
    - [ ] Application scales down when load decreases

### Cluster Lifecycle

- [ ] [Rotate SSH Keys](../operations/rotate-ssh-keys.md) — Validate key rotation procedure
- [ ] [Machine Config](../operations/machine-config.md) — Apply node-level configuration changes
- [ ] Node drain and maintenance — Cordon, drain, and uncordon a node
- [ ] Cluster upgrade tested (minor version or z-stream)
    - [ ] Pre-upgrade health check passed
    - [ ] Upgrade completed without degraded operators
    - [ ] Workloads remained available during upgrade

### Monitoring and Troubleshooting

- [ ] Monitoring dashboards accessible (Observe section in web console)
- [ ] Alerts fire correctly (trigger a test alert, verify in Alertmanager)
- [ ] `oc adm must-gather` executed and bundle reviewed
- [ ] Log collection validated (node logs, pod logs, operator logs)
- [ ] Common failure modes understood by the customer team:
    - [ ] Node NotReady
    - [ ] Pod Pending / CrashLoopBackOff / ImagePullBackOff
    - [ ] PVC Pending
    - [ ] Operator Degraded

---

## Phase 9: Results and Recommendations

### Final Validation Summary

| Category     | What Was Tested     | Expected Outcome          | Actual Outcome | Result |
| ------------ | ------------------- | ------------------------- | -------------- | ------ |
| Installation | Cluster deploy      | All nodes healthy         |                |        |
| Networking   | Traffic flow        | Routes reachable          |                |        |
| Storage      | Volume lifecycle    | PVCs provision and bind   |                |        |
| Security     | Login and RBAC      | Auth and roles enforced   |                |        |
| Applications | App deployment      | Workloads run end-to-end  |                |        |
| Resilience   | Node failure        | Workloads recover         |                |        |
| Scaling      | Add capacity        | New node joins cluster    |                |        |
| Backup       | Protect and restore | Data intact after restore |                |        |
| Monitoring   | Alert pipeline      | Alerts delivered          |                |        |
| Migration    | VM migration        | VMs operational           |                |        |
| Upgrade      | Version bump        | Upgrade succeeds cleanly  |                |        |

### Sizing and Architecture for Production

- [ ] Compute sizing documented (CPU, memory, disk per node role)
- [ ] Storage architecture and capacity plan defined
- [ ] Network topology and segmentation documented
- [ ] High-availability and DR strategy outlined
- [ ] Backup retention and RPO/RTO targets set
- [ ] Security hardening steps identified (CIS, STIG, network policies)
- [ ] Alerting and on-call strategy documented
- [ ] Operational ownership model agreed (who runs what)

### Subscription and Infrastructure Summary

- [ ] Hardware bill of materials finalized (servers, NICs, disks)
- [ ] Network allocation documented (VLANs, IP ranges, firewall rules)
- [ ] Red Hat entitlements and subscription counts confirmed
- [ ] External dependencies cataloged (storage arrays, load balancers, DNS)

---

## Phase 10: Handoff and Closure

### Operational Readiness of Customer Team

- [ ] Team has demonstrated the ability to:
    - [ ] Perform routine cluster administration
    - [ ] Diagnose and resolve common issues
    - [ ] Execute cluster upgrades
    - [ ] Add or remove cluster capacity
    - [ ] Run backup and restore procedures
    - [ ] Deploy new applications to the platform

### Artifacts Delivered

- [ ] Architecture diagram
- [ ] Installation and configuration runbook
- [ ] Day 2 operations guide
- [ ] Troubleshooting reference
- [ ] Upgrade playbook
- [ ] Backup and recovery procedure
- [ ] Escalation and support contacts

### Findings and Decision

- [ ] Successful tests documented
- [ ] Failures documented with root cause and resolution
- [ ] Gaps identified and categorized:
    - [ ] Platform gaps (features not yet available)
    - [ ] Infrastructure gaps (hardware, network, or storage shortfalls)
    - [ ] Application gaps (app-specific constraints)
    - [ ] POC-only limitations (not relevant to production)
- [ ] Lessons learned recorded for production planning
- [ ] Final go/no-go recommendation delivered and agreed

### Formal Approval

| Role                         | Name | Date |
| ---------------------------- | ---- | ---- |
| Customer Technical Lead      |      |      |
| Customer Infrastructure Lead |      |      |
| Red Hat / Partner Engineer   |      |      |
| Project Sponsor              |      |      |

---

!!! tip "Tracking Progress"
    Copy this checklist into your project tracking tool or print it for your kickoff meeting. Review progress weekly with the customer team and update the status as each milestone completes.
