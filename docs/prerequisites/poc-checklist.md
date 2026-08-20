# POC Checklist

This checklist provides a complete end-to-end baseline for validating OpenShift in your environment. It covers discovery, infrastructure preparation, installation, configuration, VM migration, workload deployment, operational validation, and formal closure.

Use this as a tracker for your POC engagement. Not every item will apply to every environment — skip sections that are out of scope for your specific goals.

[Download as Word Document](../assets/downloads/poc-checklist.docx){ .md-button }

---

## Phase 1: Discovery and Scoping

Complete this phase before any technical work begins. Align on goals, boundaries, and what a successful outcome looks like.

### Goals and Drivers

| Item                                                        | Status | Notes |
| ----------------------------------------------------------- | ------ | ----- |
| Document specific POC objectives with measurable outcomes   |        |       |
| Identify which applications or workloads will be evaluated  |        |       |
| Capture high-availability and recovery expectations         |        |       |
| Note any security, regulatory, or compliance constraints    |        |       |
| Understand target production timeline and anticipated scale |        |       |

### Boundaries and Assumptions

| Item                                                             | Status | Notes |
| ---------------------------------------------------------------- | ------ | ----- |
| Agree on what is included in the POC and document it             |        |       |
| Explicitly list what is excluded (to prevent scope creep)        |        |       |
| Document assumptions and responsibilities (customer vs. Red Hat) |        |       |
| Identify all participating teams (infra, network, security, dev) |        |       |
| Set a timeline with key milestone dates                          |        |       |

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

| Item                                                              | Status | Notes |
| ----------------------------------------------------------------- | ------ | ----- |
| Red Hat account created and subscriptions allocated               |        |       |
| Compute nodes provisioned and meet minimum specs                  |        |       |
| Management access to nodes confirmed (BMC, vCenter, cloud API)    |        |       |
| Firmware/BIOS settings validated (UEFI, virtualization extensions) |        |       |
| Network subnets allocated for cluster traffic                     |        |       |
| Firewall rules opened (API, ingress, registry access)             |        |       |
| NTP accessible from all nodes                                     |        |       |
| Load balancer configured (if required)                            |        |       |
| `api.<cluster>.<domain>` DNS record resolves correctly            |        |       |
| `*.apps.<cluster>.<domain>` wildcard DNS resolves correctly       |        |       |
| Reverse DNS entries (PTR) configured                              |        |       |
| Persistent storage backend provisioned and accessible             |        |       |
| Storage connectivity verified from node networks                  |        |       |
| `oc` CLI installed on installation host                           |        |       |
| Pull secret downloaded from Red Hat console                       |        |       |
| SSH key pair generated                                            |        |       |

---

## Phase 3: Installation

| Item                                                              | Status | Notes |
| ----------------------------------------------------------------- | ------ | ----- |
| Installation method selected                                      |        |       |
| Cluster installation completed successfully                       |        |       |
| All nodes showing `Ready` status                                  |        |       |
| All ClusterOperators Available=True, Degraded=False               |        |       |
| Cluster version matches target release                            |        |       |
| Web console accessible                                            |        |       |
| `kubeadmin` credentials stored securely                           |        |       |

---

## Phase 4: Post-Installation (Required)

These must be completed before deploying workloads.

| Item                                                              | Status | Notes |
| ----------------------------------------------------------------- | ------ | ----- |
| Advanced networking operator installed (if using bonds/VLANs)     |        |       |
| Storage driver installed and StorageClasses created               |        |       |
| Default StorageClass set                                          |        |       |
| RWO PVC created and bound successfully                            |        |       |
| RWX PVC created and bound successfully (if applicable)            |        |       |
| Internal image registry configured with persistent storage        |        |       |

---

## Phase 5: Post-Installation (Optional)

Install based on your POC goals. Each subsection is independent.

### Networking

| Item                                                              | Status | Notes |
| ----------------------------------------------------------------- | ------ | ----- |
| Additional network configuration applied (bridges, secondary NICs)|        |       |
| Pod-to-pod communication verified across nodes                    |        |       |
| Ingress/Route exposes an application externally                   |        |       |
| DNS resolution works from within pods (internal and external)     |        |       |

### Virtualization

| Item                                                              | Status | Notes |
| ----------------------------------------------------------------- | ------ | ----- |
| OpenShift Virtualization operator installed                       |        |       |
| HyperConverged CR created                                         |        |       |
| Live migration network configured (if applicable)                 |        |       |
| Node health check and remediation operators installed             |        |       |
| Health check CRs created (workers and control plane)              |        |       |
| Descheduler operator installed and configured                     |        |       |

### Migration

| Item                                                              | Status | Notes |
| ----------------------------------------------------------------- | ------ | ----- |
| Migration toolkit operator installed                              |        |       |
| Source virtualization provider added                               |        |       |
| Network and storage mappings configured                           |        |       |

### Backup and Restore

| Item                                                              | Status | Notes |
| ----------------------------------------------------------------- | ------ | ----- |
| Backup operator installed                                         |        |       |
| Backup storage location configured                                |        |       |
| DataProtectionApplication CR created                              |        |       |

### Observability

| Item                                                              | Status | Notes |
| ----------------------------------------------------------------- | ------ | ----- |
| Cluster logging configured                                        |        |       |
| Network observability enabled                                     |        |       |
| Multi-cluster observability configured (if multi-cluster)         |        |       |

### Security and Access

| Item                                                              | Status | Notes |
| ----------------------------------------------------------------- | ------ | ----- |
| Identity provider configured (LDAP, OIDC, etc.)                   |        |       |
| RBAC groups mapped correctly (members get expected roles)         |        |       |
| `kubeadmin` secret removed after IdP verification (if desired)    |        |       |
| Non-production banner applied to the console                      |        |       |

---

## Phase 6: VM Migration

Validate that virtual machines can be migrated from an existing virtualization platform to OpenShift Virtualization.

| Item                                                              | Status | Notes |
| ----------------------------------------------------------------- | ------ | ----- |
| Source virtualization environment accessible from OpenShift        |        |       |
| Migration provider connection healthy                             |        |       |
| Target storage class selected                                     |        |       |
| Target network mapping configured                                 |        |       |
| VMs selected for migration                                        |        |       |
| Cold migration executed — VM boots on OpenShift                   |        |       |
| Networking functional (IP, DNS, connectivity)                     |        |       |
| Storage attached and data intact                                  |        |       |
| Applications inside the VM running correctly                      |        |       |
| Warm migration tested — cutover with minimal downtime             |        |       |
| VM accessible via console and SSH post-migration                  |        |       |

---

## Phase 7: Workloads

Deploy workloads to validate platform capabilities.

### Container Workloads

| Item                                                              | Status | Notes |
| ----------------------------------------------------------------- | ------ | ----- |
| Basic container deployed and accessible via Route                 |        |       |
| Build from source — image built and app deploys                   |        |       |
| Stateful application — data persists across pod restarts          |        |       |
| Multi-tier application — frontend and backend communicating       |        |       |
| Event streaming workload deployed (if applicable)                 |        |       |
| Customer application deployed (if provided)                       |        |       |

### Virtual Machine Workloads

| Item                                                              | Status | Notes |
| ----------------------------------------------------------------- | ------ | ----- |
| VM deployed from template — boots, SSH, storage functional        |        |       |
| Live migration tested (move VM between nodes without downtime)    |        |       |
| Snapshot and restore tested                                       |        |       |

---

## Phase 8: Operational Validation

Demonstrate Day 2 operations and resilience.

### Failover and Resilience

| Item                                                              | Status | Notes |
| ----------------------------------------------------------------- | ------ | ----- |
| Node failure simulated                                            |        |       |
| VM restarted on healthy node within target time                   |        |       |
| Application recovered without manual intervention                 |        |       |
| Container pod rescheduled to healthy node after failure           |        |       |
| Service remained available during failover                        |        |       |

### Backup and Restore

| Item                                                              | Status | Notes |
| ----------------------------------------------------------------- | ------ | ----- |
| Application or VM backup completed successfully                   |        |       |
| Restore to same or different namespace validated                  |        |       |
| Data integrity confirmed after restore                            |        |       |

### Cluster Lifecycle

| Item                                                              | Status | Notes |
| ----------------------------------------------------------------- | ------ | ----- |
| SSH key rotation validated                                        |        |       |
| Node-level configuration change applied via MachineConfig         |        |       |
| Node drain and maintenance — cordon, drain, uncordon              |        |       |
| Cluster upgrade tested (minor version or z-stream)                |        |       |
| Workloads remained available during upgrade                       |        |       |
| Worker node added — new node joins cluster successfully           |        |       |

### Monitoring and Troubleshooting

| Item                                                              | Status | Notes |
| ----------------------------------------------------------------- | ------ | ----- |
| Monitoring dashboards accessible                                  |        |       |
| Alerts fire correctly (trigger test alert, verify delivery)       |        |       |
| Diagnostic bundle collected and reviewed                          |        |       |
| Log collection validated (node, pod, operator logs)               |        |       |
| Common failure modes understood by the customer team              |        |       |

---

## Phase 9: Results Summary

Complete this table during the POC to prepare for the closeout meeting readout.

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

---

## Phase 10: Closeout

### Deliverables

The POC concludes with two formal deliverables:

1. **Completed checklist** — this document, filled in with status and notes for every item tested.
2. **Closeout meeting** — a readout of all POC findings, outcomes, gaps, and recommendations presented to stakeholders.

### Findings Summary

| Item                                                              | Status | Notes |
| ----------------------------------------------------------------- | ------ | ----- |
| Successful tests documented                                       |        |       |
| Failures documented with root cause and resolution                |        |       |
| Platform gaps identified (features not yet available)             |        |       |
| Infrastructure gaps identified (hardware, network, storage)       |        |       |
| Application gaps identified (app-specific constraints)            |        |       |
| POC-only limitations noted (not relevant to production)           |        |       |
| Lessons learned recorded for production planning                  |        |       |
| Final go/no-go recommendation delivered and agreed                |        |       |

### Operational Readiness of Customer Team

The customer team has demonstrated the ability to:

| Item                                             | Status | Notes |
| ------------------------------------------------ | ------ | ----- |
| Perform routine cluster administration           |        |       |
| Diagnose and resolve common issues               |        |       |
| Execute cluster upgrades                         |        |       |
| Add or remove cluster capacity                   |        |       |
| Run backup and restore procedures                |        |       |
| Deploy new applications to the platform          |        |       |

---

## Follow-Up: Sizing and Proposal

Upon successful completion of the POC, the next step is a sizing and proposal process that translates POC findings into a production-ready architecture and commercial agreement.

| Item                                                              | Status | Notes |
| ----------------------------------------------------------------- | ------ | ----- |
| Compute sizing documented (CPU, memory, disk per node role)       |        |       |
| Storage architecture and capacity plan defined                    |        |       |
| Network topology and segmentation documented                      |        |       |
| High-availability and DR strategy outlined                        |        |       |
| Backup retention and RPO/RTO targets set                          |        |       |
| Security hardening steps identified                               |        |       |
| Alerting and on-call strategy documented                          |        |       |
| Operational ownership model agreed (who runs what)                |        |       |
| Hardware bill of materials finalized                              |        |       |
| Network allocation documented (subnets, IPs, firewall rules)     |        |       |
| Red Hat entitlements and subscription counts confirmed            |        |       |
| External dependencies cataloged (storage, load balancers, DNS)   |        |       |
| Commercial proposal delivered to customer                         |        |       |

---

!!! tip "Tracking Progress"
    Use the downloadable Word document for offline tracking or print it for your kickoff meeting. Review progress weekly with the customer team and update the status as each milestone completes.
