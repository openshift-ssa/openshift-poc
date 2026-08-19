# POC Checklist

This checklist provides a complete end-to-end baseline for validating OpenShift in your environment. It covers discovery, infrastructure preparation, installation, configuration, VM migration, workload deployment, operational validation, and formal closure.

Use this as a tracker for your POC engagement. Not every item will apply to every environment — skip sections that are out of scope for your specific goals.

[Download as Word Document](../assets/downloads/poc-checklist.docx){ .md-button }

---

## Phase 1: Discovery and Scoping

Complete this phase before any technical work begins. Align on goals, boundaries, and what a successful outcome looks like.

### Goals and Drivers

| #  | Item                                                        | Status | Notes |
| -- | ----------------------------------------------------------- | ------ | ----- |
| 1  | Define the core business problem OpenShift will address     |        |       |
| 2  | Document specific POC objectives with measurable outcomes   |        |       |
| 3  | Identify which applications or workloads will be evaluated  |        |       |
| 4  | Capture high-availability and recovery expectations         |        |       |
| 5  | Note any security, regulatory, or compliance constraints    |        |       |
| 6  | Understand target production timeline and anticipated scale |        |       |

### Boundaries and Assumptions

| #  | Item                                                             | Status | Notes |
| -- | ---------------------------------------------------------------- | ------ | ----- |
| 7  | Agree on what is included in the POC and document it             |        |       |
| 8  | Explicitly list what is excluded (to prevent scope creep)        |        |       |
| 9  | Document assumptions and responsibilities (customer vs. Red Hat) |        |       |
| 10 | Identify all participating teams (infra, network, security, dev) |        |       |
| 11 | Set a timeline with key milestone dates                          |        |       |

### Exit Criteria

Agree on pass/fail criteria before installation begins:

| Area         | How We Measure Success                            | Status |
| ------------ | ------------------------------------------------- | ------ |
| Installation | Cluster deployed, all nodes healthy               |        |
| Networking   | Application traffic flows end-to-end              |        |
| Storage      | Persistent volumes provision and bind on demand   |        |
| Security     | Users authenticate and RBAC enforces permissions  |        |
| Applications | Sample and customer workloads run correctly       |        |
| Resilience   | Cluster recovers from simulated failures          |        |
| Operations   | Monitoring, logging, and backups function         |        |
| Migration    | VMs migrated to OpenShift (if applicable)         |        |

---

## Phase 2: Prerequisites

Complete these before scheduling the installation.

| #  | Item                                                              | Status | Notes |
| -- | ----------------------------------------------------------------- | ------ | ----- |
| 1  | Red Hat account created and subscriptions allocated               |        |       |
| 2  | Compute nodes provisioned and meet minimum specs                  |        |       |
| 3  | Management access to nodes confirmed (BMC, vCenter, cloud API)    |        |       |
| 4  | Firmware/BIOS settings validated (UEFI, virtualization extensions) |        |       |
| 5  | Network subnets allocated for cluster traffic                     |        |       |
| 6  | Firewall rules opened (API, ingress, registry access)             |        |       |
| 7  | NTP accessible from all nodes                                     |        |       |
| 8  | Load balancer configured (if required)                            |        |       |
| 9  | `api.<cluster>.<domain>` DNS record resolves correctly            |        |       |
| 10 | `*.apps.<cluster>.<domain>` wildcard DNS resolves correctly       |        |       |
| 11 | Reverse DNS entries (PTR) configured                              |        |       |
| 12 | Persistent storage backend provisioned and accessible             |        |       |
| 13 | Storage connectivity verified from node networks                  |        |       |
| 14 | `oc` CLI installed on installation host                           |        |       |
| 15 | Pull secret downloaded from Red Hat console                       |        |       |
| 16 | SSH key pair generated                                            |        |       |

---

## Phase 3: Installation

| #  | Item                                                              | Status | Notes |
| -- | ----------------------------------------------------------------- | ------ | ----- |
| 1  | Installation method selected                                      |        |       |
| 2  | Cluster installation completed successfully                       |        |       |
| 3  | All nodes showing `Ready` status                                  |        |       |
| 4  | All ClusterOperators Available=True, Degraded=False               |        |       |
| 5  | Cluster version matches target release                            |        |       |
| 6  | Web console accessible                                            |        |       |
| 7  | `kubeadmin` credentials stored securely                           |        |       |

---

## Phase 4: Post-Installation (Required)

These must be completed before deploying workloads.

| #  | Item                                                              | Status | Notes |
| -- | ----------------------------------------------------------------- | ------ | ----- |
| 1  | Advanced networking operator installed (if using bonds/VLANs)     |        |       |
| 2  | Storage driver installed and StorageClasses created               |        |       |
| 3  | Default StorageClass set                                          |        |       |
| 4  | RWO PVC created and bound successfully                            |        |       |
| 5  | RWX PVC created and bound successfully (if applicable)            |        |       |
| 6  | Internal image registry configured with persistent storage        |        |       |

---

## Phase 5: Post-Installation (Optional)

Install based on your POC goals. Each subsection is independent.

### Networking

| #  | Item                                                              | Status | Notes |
| -- | ----------------------------------------------------------------- | ------ | ----- |
| 1  | Additional network configuration applied (bridges, secondary NICs)|        |       |
| 2  | Pod-to-pod communication verified across nodes                    |        |       |
| 3  | Ingress/Route exposes an application externally                   |        |       |
| 4  | DNS resolution works from within pods (internal and external)     |        |       |

### Virtualization

| #  | Item                                                              | Status | Notes |
| -- | ----------------------------------------------------------------- | ------ | ----- |
| 1  | OpenShift Virtualization operator installed                       |        |       |
| 2  | HyperConverged CR created                                         |        |       |
| 3  | Live migration network configured (if applicable)                 |        |       |
| 4  | Node health check and remediation operators installed             |        |       |
| 5  | Health check CRs created (workers and control plane)              |        |       |
| 6  | Descheduler operator installed and configured                     |        |       |

### Migration

| #  | Item                                                              | Status | Notes |
| -- | ----------------------------------------------------------------- | ------ | ----- |
| 1  | Migration toolkit operator installed                              |        |       |
| 2  | Source virtualization provider added                               |        |       |
| 3  | Network and storage mappings configured                           |        |       |

### Backup and Restore

| #  | Item                                                              | Status | Notes |
| -- | ----------------------------------------------------------------- | ------ | ----- |
| 1  | Backup operator installed                                         |        |       |
| 2  | Backup storage location configured                                |        |       |
| 3  | DataProtectionApplication CR created                              |        |       |

### Observability

| #  | Item                                                              | Status | Notes |
| -- | ----------------------------------------------------------------- | ------ | ----- |
| 1  | Cluster logging configured                                        |        |       |
| 2  | Network observability enabled                                     |        |       |
| 3  | Multi-cluster observability configured (if multi-cluster)         |        |       |

### Developer Experience

| #  | Item                                                              | Status | Notes |
| -- | ----------------------------------------------------------------- | ------ | ----- |
| 1  | Web terminal enabled                                              |        |       |
| 2  | External secrets integration configured (if applicable)           |        |       |

### Security and Access

| #  | Item                                                              | Status | Notes |
| -- | ----------------------------------------------------------------- | ------ | ----- |
| 1  | Identity provider configured (LDAP, OIDC, etc.)                   |        |       |
| 2  | RBAC groups mapped correctly (members get expected roles)         |        |       |
| 3  | `kubeadmin` secret removed after IdP verification (if desired)    |        |       |
| 4  | Non-production banner applied to the console                      |        |       |

---

## Phase 6: VM Migration

Validate that virtual machines can be migrated from an existing virtualization platform to OpenShift Virtualization.

| #  | Item                                                              | Status | Notes |
| -- | ----------------------------------------------------------------- | ------ | ----- |
| 1  | Source virtualization environment accessible from OpenShift        |        |       |
| 2  | Migration provider connection healthy                             |        |       |
| 3  | Target storage class selected                                     |        |       |
| 4  | Target network mapping configured                                 |        |       |
| 5  | VMs selected for migration                                        |        |       |
| 6  | Cold migration executed — VM boots on OpenShift                   |        |       |
| 7  | Networking functional (IP, DNS, connectivity)                     |        |       |
| 8  | Storage attached and data intact                                  |        |       |
| 9  | Applications inside the VM running correctly                      |        |       |
| 10 | Warm migration tested — cutover with minimal downtime             |        |       |
| 11 | VM accessible via console and SSH post-migration                  |        |       |

---

## Phase 7: Workloads

Deploy workloads to validate platform capabilities.

### Container Workloads

| #  | Item                                                              | Status | Notes |
| -- | ----------------------------------------------------------------- | ------ | ----- |
| 1  | Basic container deployed and accessible via Route                 |        |       |
| 2  | Build from source — image built and app deploys                   |        |       |
| 3  | Stateful application — data persists across pod restarts          |        |       |
| 4  | Multi-tier application — frontend and backend communicating       |        |       |
| 5  | Event streaming workload deployed (if applicable)                 |        |       |
| 6  | Customer application deployed (if provided)                       |        |       |

### Virtual Machine Workloads

| #  | Item                                                              | Status | Notes |
| -- | ----------------------------------------------------------------- | ------ | ----- |
| 1  | VM deployed from template — boots, SSH, storage functional        |        |       |
| 2  | Live migration tested (move VM between nodes without downtime)    |        |       |
| 3  | Snapshot and restore tested                                       |        |       |

---

## Phase 8: Operational Validation

Demonstrate Day 2 operations and resilience.

### Failover and Resilience

| #  | Item                                                              | Status | Notes |
| -- | ----------------------------------------------------------------- | ------ | ----- |
| 1  | Node failure simulated                                            |        |       |
| 2  | VM restarted on healthy node within target time                   |        |       |
| 3  | Application recovered without manual intervention                 |        |       |
| 4  | Container pod rescheduled to healthy node after failure           |        |       |
| 5  | Service remained available during failover                        |        |       |

### Backup and Restore

| #  | Item                                                              | Status | Notes |
| -- | ----------------------------------------------------------------- | ------ | ----- |
| 1  | Application or VM backup completed successfully                   |        |       |
| 2  | Restore to same or different namespace validated                  |        |       |
| 3  | Data integrity confirmed after restore                            |        |       |
| 4  | etcd backup taken and stored securely off-cluster                 |        |       |

### Scaling

| #  | Item                                                              | Status | Notes |
| -- | ----------------------------------------------------------------- | ------ | ----- |
| 1  | Worker node added — new node joins cluster successfully           |        |       |

### Cluster Lifecycle

| #  | Item                                                              | Status | Notes |
| -- | ----------------------------------------------------------------- | ------ | ----- |
| 1  | SSH key rotation validated                                        |        |       |
| 2  | Node-level configuration change applied via MachineConfig         |        |       |
| 3  | Node drain and maintenance — cordon, drain, uncordon              |        |       |
| 4  | Cluster upgrade tested (minor version or z-stream)                |        |       |
| 5  | Workloads remained available during upgrade                       |        |       |

### Monitoring and Troubleshooting

| #  | Item                                                              | Status | Notes |
| -- | ----------------------------------------------------------------- | ------ | ----- |
| 1  | Monitoring dashboards accessible                                  |        |       |
| 2  | Alerts fire correctly (trigger test alert, verify delivery)       |        |       |
| 3  | Diagnostic bundle collected and reviewed                          |        |       |
| 4  | Log collection validated (node, pod, operator logs)               |        |       |
| 5  | Common failure modes understood by the customer team              |        |       |

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

| #  | Item                                                              | Status | Notes |
| -- | ----------------------------------------------------------------- | ------ | ----- |
| 1  | Compute sizing documented (CPU, memory, disk per node role)       |        |       |
| 2  | Storage architecture and capacity plan defined                    |        |       |
| 3  | Network topology and segmentation documented                      |        |       |
| 4  | High-availability and DR strategy outlined                        |        |       |
| 5  | Backup retention and RPO/RTO targets set                          |        |       |
| 6  | Security hardening steps identified                               |        |       |
| 7  | Alerting and on-call strategy documented                          |        |       |
| 8  | Operational ownership model agreed (who runs what)                |        |       |

### Subscription and Infrastructure Summary

| #  | Item                                                              | Status | Notes |
| -- | ----------------------------------------------------------------- | ------ | ----- |
| 1  | Hardware bill of materials finalized                              |        |       |
| 2  | Network allocation documented (subnets, IPs, firewall rules)     |        |       |
| 3  | Red Hat entitlements and subscription counts confirmed            |        |       |
| 4  | External dependencies cataloged (storage, load balancers, DNS)   |        |       |

---

## Phase 10: Handoff and Closure

### Operational Readiness of Customer Team

| #  | Item                                             | Status | Notes |
| -- | ------------------------------------------------ | ------ | ----- |
| 1  | Perform routine cluster administration           |        |       |
| 2  | Diagnose and resolve common issues               |        |       |
| 3  | Execute cluster upgrades                         |        |       |
| 4  | Add or remove cluster capacity                   |        |       |
| 5  | Run backup and restore procedures                |        |       |
| 6  | Deploy new applications to the platform          |        |       |

### Artifacts Delivered

| #  | Item                                             | Status | Notes |
| -- | ------------------------------------------------ | ------ | ----- |
| 1  | Architecture diagram                             |        |       |
| 2  | Installation and configuration runbook           |        |       |
| 3  | Day 2 operations guide                           |        |       |
| 4  | Troubleshooting reference                        |        |       |
| 5  | Upgrade playbook                                 |        |       |
| 6  | Backup and recovery procedure                    |        |       |
| 7  | Escalation and support contacts                  |        |       |

### Findings and Decision

| #  | Item                                                              | Status | Notes |
| -- | ----------------------------------------------------------------- | ------ | ----- |
| 1  | Successful tests documented                                       |        |       |
| 2  | Failures documented with root cause and resolution                |        |       |
| 3  | Platform gaps identified (features not yet available)              |        |       |
| 4  | Infrastructure gaps identified (hardware, network, storage)       |        |       |
| 5  | Application gaps identified (app-specific constraints)            |        |       |
| 6  | POC-only limitations noted (not relevant to production)           |        |       |
| 7  | Lessons learned recorded for production planning                  |        |       |
| 8  | Final go/no-go recommendation delivered and agreed                |        |       |

### Formal Approval

| Role                         | Name | Date |
| ---------------------------- | ---- | ---- |
| Customer Technical Lead      |      |      |
| Customer Infrastructure Lead |      |      |
| Red Hat / Partner Engineer   |      |      |
| Project Sponsor              |      |      |

---

!!! tip "Tracking Progress"
    Use the downloadable Word document for offline tracking or print it for your kickoff meeting. Review progress weekly with the customer team and update the status as each milestone completes.
