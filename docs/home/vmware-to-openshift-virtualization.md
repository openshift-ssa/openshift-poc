# From VMware to OpenShift Virtualization

Organizations moving off VMware are not giving up virtualization capabilities — they are consolidating them onto the same platform that already runs their containers. **Anything you can do in VMware, you can do in OpenShift Virtualization.** The APIs, tools, and operational patterns are different; the outcomes are the same, and in most cases the OpenShift approach is stronger because it is Kubernetes-native, declarative, and shared with container workloads.

This page covers what a migration involves and how major VMware capabilities map to OpenShift Virtualization. For hands-on steps in this POC, see [OpenShift Virtualization](../configure-the-cluster/virtualization.md) and [Migration Toolkit for Virtualization](../configure-the-cluster/mtv.md).

## Guiding principle

| VMware mindset                                                                   | OpenShift Virtualization mindset                                                                |
| -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Proprietary hypervisor + management stack (ESXi + vCenter + optional NSX / Aria) | Open platform: KVM via KubeVirt, managed as first-class Kubernetes objects                      |
| GUI-first day-2 operations                                                       | Same UI when you want it; every action is also an API object you can GitOps and automate        |
| Separate stack for VMs vs containers                                             | One cluster, one networking model, one storage CSI plane, one RBAC model for VMs and containers |
| Feature X only exists in product Y                                               | Feature X is expressed with Kubernetes primitives (often simpler, always inspectable as YAML)   |

The rest of this document walks feature by feature. For each area: what VMware provides, how OpenShift Virtualization delivers the equivalent, and why the OpenShift path is typically better.

## What migration involves

A VMware-to-OpenShift Virtualization migration is more than copying disks. Treat it as a platform cutover with clear phases.

```mermaid
flowchart LR
    assess[Assess] --> prepare[Prepare platform]
    prepare --> pilot[Pilot migrate]
    pilot --> wave[Wave migrate]
    wave --> optimize[Optimize and retire]
```

### 1. Assess the VMware estate

Inventory what must move and what must change:

| Area         | What to capture                                                                                          |
| ------------ | -------------------------------------------------------------------------------------------------------- |
| Workloads    | VM count, OS, CPU/RAM, disks, boot order, applications, owners                                           |
| Networking   | Port groups, VLANs, NSX segments, load balancers, firewall / microseg rules, IP persistence requirements |
| Storage      | Datastores, vSAN policies, snapshots, replication, backup products                                       |
| Availability | vSphere HA / DRS affinity, FT, stretched clusters, RPO/RTO                                               |
| Operations   | PowerCLI / Aria automation, monitoring, patching, identity, change process                               |
| Dependencies | Shared services still on VMware, appliances, licensing, compliance controls                              |

Flag VMs that need a secondary underlay (stable IPs on a VLAN), RWX storage for live migration, or guest tools equivalent (`qemu-guest-agent`).

### 2. Prepare the OpenShift platform

Before the first production VM lands:

1. Install and size a cluster that meets [prerequisites](../prerequisites/index.md) (especially storage and networking).
2. Configure [storage](../configure-the-cluster/storage/index.md) with a default virt StorageClass and **RWX** where live migration is required.
3. Install [NMState](../configure-the-cluster/nmstate.md) and any [underlay / CUDN networks](../configure-the-cluster/networking.md) VMs need for IP sameness.
4. Install [OpenShift Virtualization](../configure-the-cluster/virtualization.md).
5. If you will test node-loss failover, install [Workload Availability](../configure-the-cluster/workload-availability.md) **before** Virtualization.
6. Install [MTV](../configure-the-cluster/mtv.md) and obtain the VDDK image early (required for warm and vSAN migrations).
7. Align identity, [network policy](../configure-the-cluster/network-policy.md), [monitoring](../configure-the-cluster/monitoring.md), and [backup](../configure-the-cluster/oadp.md) with how you will operate after cutover.

### 3. Migrate with MTV

[Migration Toolkit for Virtualization (MTV)](../configure-the-cluster/mtv.md) is the supported path from vSphere (and other hypervisors) into OpenShift Virtualization:

| Migration mode | When to use it                        | Notes                                            |
| -------------- | ------------------------------------- | ------------------------------------------------ |
| Cold           | Maintenance windows OK; simplest path | VM powered off; VDDK optional (faster with VDDK) |
| Warm           | Minimize downtime for large disks     | Precopy while running; cutover; VDDK required    |
| OVA            | Appliances / offline images           | Useful when live vCenter access is constrained   |

Typical wave plan:

1. **Pilot** — non-critical VMs; validate networking, storage class, guest agent, backup, and failover.
2. **Wave by affinity** — migrate application tiers together; rewrite load balancers and DNS as you go.
3. **Cutover** — final sync, power-off source (or quarantine), validate, update runbooks.
4. **Decommission** — retire vSphere capacity after soak period.

### 4. Operate and optimize

After migration, shift from vSphere-centric ops to Kubernetes-centric ops: declare VMs as YAML, manage namespaces as tenancy boundaries, use GitOps for drift control, and share the same observability and policy plane with containers. Many organizations then modernize selectively (replatform some apps to containers) while keeping other workloads as VMs — on one platform.

---

## Feature-by-feature comparison

### At a glance

| VMware capability              | OpenShift Virtualization equivalent        | Why OpenShift is stronger                                                  |
| ------------------------------ | ------------------------------------------ | -------------------------------------------------------------------------- |
| ESXi + vCenter                 | KVM + KubeVirt on OpenShift                | One API for VMs and containers; declarative, GitOps-friendly               |
| vMotion                        | Live migration                             | Same outcome; scheduled/automated with eviction strategies and descheduler |
| vSphere HA                     | Workload Availability + Kubernetes         | Faster, policy-driven remediation integrated with cluster health           |
| DRS                            | Scheduler + Descheduler                    | Continuous rebalancing with Kubernetes resource model                      |
| vSAN / VMFS / NFS              | CSI (ODF, vendor CSI)                      | Standard PVCs; same storage for pods and VMs                               |
| NSX-T microsegmentation        | NetworkPolicy + MultiNetworkPolicy         | Kubernetes-native, GitOps, no separate SDN product tax                     |
| NSX / AVI load balancing       | Services, Routes, MetalLB / ingress        | Built into the platform; consistent for pods and VMs                       |
| Content Library / templates    | Templates, DataVolumes, InstanceTypes      | Versionable YAML; clone from PVC/DV pipeline                               |
| Snapshots / Veeam-style backup | VolumeSnapshots + OADP                     | Application- and VM-aware backups on the same API                          |
| PowerCLI / Aria                | `oc` / Kubernetes API / OpenShift GitOps   | Universal automation surface; no VM-only scripting island                  |
| vSphere RBAC                   | Projects + RBAC + SCCs / PSA               | Fine-grained, auditable, multi-tenant by default                           |
| vRealize / Aria Ops            | Monitoring, Logging, Network Observability | Prometheus-native metrics shared with the whole cluster                    |
| VMware Tools                   | qemu-guest-agent                           | Standard guest agent; works with live migration and readiness              |

### Compute and hypervisor

| VMware                         | OpenShift Virtualization                                          |
| ------------------------------ | ----------------------------------------------------------------- |
| ESXi hosts managed by vCenter  | Worker nodes run VMs as `VirtualMachine` objects (KubeVirt / CNV) |
| VM hardware versions, .vmx     | InstanceTypes, Preferences, and VM specs in YAML                  |
| Dedicated virt admin skill set | Same skills as operating OpenShift for containers                 |

**Why OpenShift is better:** You stop operating a second control plane. Capacity, upgrades, and node lifecycle are cluster operations. VMs appear in the same inventory and scheduling domain as pods, which simplifies capacity planning and eliminates the "two clouds in one DC" tax.

### Live migration (vMotion)

| VMware                                    | OpenShift Virtualization                                                           |
| ----------------------------------------- | ---------------------------------------------------------------------------------- |
| vMotion between ESXi hosts                | Live migration between worker nodes                                                |
| Requires shared storage / vMotion network | Requires RWX (or appropriate shared) storage; optional dedicated migration network |

**Why OpenShift is better:** Eviction is declarative (`evictionStrategy: LiveMigrate`). Combined with the [Descheduler](../configure-the-cluster/workload-availability.md), VMs move under load or during maintenance without a separate DRS product. Migration traffic can be isolated on its own VLAN like a vMotion network — configured with NMState and the HyperConverged CR — while remaining part of the same cluster config.

### High availability and failover

| VMware                                  | OpenShift Virtualization                                                                                                                                 |
| --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| vSphere HA restarts VMs on host failure | [Workload Availability](../configure-the-cluster/workload-availability.md): Node Health Check + Self Node Remediation restart workloads on healthy nodes |
| FT for lockstep VMs                     | Architecture-dependent; prefer app-level HA or multiple replicas                                                                                         |

**Why OpenShift is better:** Remediation is explicit, tunable, and observable as Kubernetes objects. You can target ~120s VM failover from node failure to restart (see Workload Availability guidance), and the same machinery protects container workloads. There is no separate HA license tier bolted onto the hypervisor.

### Resource scheduling (DRS)

| VMware                       | OpenShift Virtualization                         |
| ---------------------------- | ------------------------------------------------ |
| DRS affinity / anti-affinity | Pod/VM affinity, topology spread, node selectors |
| Automated load balancing     | Kubernetes scheduler + Descheduler               |

**Why OpenShift is better:** Scheduling decisions use the same CPU/memory model as containers. Affinity rules are portable YAML, not vCenter inventory objects tied to a single vCenter. Descheduler continuously corrects imbalance instead of only acting at power-on or manual rebalance.

### Storage

| VMware                        | OpenShift Virtualization                             |
| ----------------------------- | ---------------------------------------------------- |
| VMFS, NFS, vSAN datastores    | CSI volumes (ODF, NetApp, Dell, Pure, …) as PVCs     |
| Storage policies / SPBM       | StorageClasses, volume modes, access modes (RWO/RWX) |
| Linked clones / instant clone | DataVolume cloning, golden images, snapshots         |

**Why OpenShift is better:** One CSI ecosystem for pods and VMs. You pick the StorageClass that matches the SLA instead of maintaining parallel datastore designs. Live migration and backup integrate with standard Kubernetes volume APIs rather than proprietary VMDK tooling alone. See [Storage](../configure-the-cluster/storage/index.md) and [ODF](../configure-the-cluster/storage/odf.md).

### Networking and microsegmentation (NSX-T)

This is the clearest example of "same outcome, better mechanism."

| VMware (NSX-T)                    | OpenShift Virtualization                                                 |
| --------------------------------- | ------------------------------------------------------------------------ |
| Segments, T0/T1 gateways, DFW     | OVN-Kubernetes pod network + secondary networks (NAD / CUDN / localnet)  |
| Distributed firewall rules        | `NetworkPolicy` (primary) and `MultiNetworkPolicy` (secondary / VM NICs) |
| Separate NSX managers & licensing | Built into OpenShift networking; enable multi-network policy when needed |

On VMware, microsegmentation usually means buying, operating, and troubleshooting NSX-T: managers, transport nodes, distributed firewall rule sets, and a skill set distinct from the rest of the DC. On OpenShift, the default deny / allow-list model is expressed as Kubernetes policy objects that select workloads by label (and `ipBlock` for VMs on secondary networks).

```yaml
# Conceptual shape — isolate a VM tier, then allow only a client CIDR
apiVersion: k8s.cni.cncf.io/v1beta1
kind: MultiNetworkPolicy
metadata:
  name: allow-clients-to-app-vms
  namespace: {{ ns }}
  annotations:
    k8s.v1.cni.cncf.io/policy-for: {{ ns }}/{{ nad_name }}
spec:
  podSelector:
    matchLabels:
      app: payments
  policyTypes:
    - Ingress
  ingress:
    - from:
        - ipBlock:
            cidr: 10.20.0.0/16
      ports:
        - protocol: TCP
          port: 443
```

**Why OpenShift is better:**

- **No second SDN product** — OVN-Kubernetes and policy controllers ship with the platform; you are not licensing and patching NSX alongside vCenter.
- **Same model for pods and VMs** — microseg for containers (`NetworkPolicy`) and for VMs on secondary NICs (`MultiNetworkPolicy`) share the same mental model and GitOps pipeline.
- **Declarative and reviewable** — rules are YAML in Git, not opaque DFW rule tables living only in an NSX UI.
- **Observable** — [Network Observability](../configure-the-cluster/network-observability.md) shows allowed and denied flows after policies land.
- **Additive allow-list** — deny-by-default is the natural first step; you open only what each tier needs.

Hands-on patterns for both containers and VMs: [Network Policy and Microsegmentation](../configure-the-cluster/network-policy.md).

### Load balancing and ingress

| VMware                    | OpenShift Virtualization                                                       |
| ------------------------- | ------------------------------------------------------------------------------ |
| NSX LB, AVI, external ADC | `Service` (ClusterIP / NodePort / LoadBalancer), Routes, MetalLB / ingress VIP |

**Why OpenShift is better:** North-south and east-west patterns are native Kubernetes. The same Route / Service constructs expose container apps and can front VM-backed Services. You standardize on one ingress architecture instead of an ADC silo for VMs and a different path for containers.

### Templates, cloning, and golden images

| VMware                     | OpenShift Virtualization                              |
| -------------------------- | ----------------------------------------------------- |
| Content Library, templates | VM templates, InstanceTypes, Preferences, DataVolumes |
| Linked clones              | PVC / DataVolume clone from golden image              |

**Why OpenShift is better:** Golden images and VM specs are version-controlled artifacts. Provisioning is an API apply (or console wizard that produces the same objects), which fits CI/CD and [OpenShift GitOps](../configure-the-cluster/openshift-gitops.md) without PowerCLI wrappers.

### Snapshots, backup, and DR

| VMware                     | OpenShift Virtualization                                                       |
| -------------------------- | ------------------------------------------------------------------------------ |
| VM snapshots, VADP backup  | VolumeSnapshots; [OADP](../configure-the-cluster/oadp.md) with kubevirt plugin |
| SRM / replication products | Storage replication + OADP / app-level DR; ACM for multi-cluster               |

**Why OpenShift is better:** Backup is application-aware on the same API used for containers. You can validate restore in this POC with [VM Backup and Restore](../workloads-and-operations/operational-validation/vm-backup-restore.md). Multi-cluster DR aligns with hub-and-spoke patterns ([Architecture](./architecture.md)) instead of a VMware-only SRM stack.

### Automation and day-2 operations

| VMware                    | OpenShift Virtualization                                             |
| ------------------------- | -------------------------------------------------------------------- |
| PowerCLI, Aria Automation | Kubernetes API, `oc`, Ansible, Terraform providers, OpenShift GitOps |
| Host profiles             | MachineConfig / Machine Config Operator                              |

**Why OpenShift is better:** Every VM create, network attachment, and policy change is a REST/API object. That collapses automation onto tools your platform team already uses for containers — one pipeline, one audit trail, one drift-detection model.

### Identity, tenancy, and RBAC

| VMware                      | OpenShift Virtualization                                  |
| --------------------------- | --------------------------------------------------------- |
| vCenter roles / permissions | OpenShift projects (namespaces), RBAC, identity providers |
| Resource pools              | ResourceQuotas, LimitRanges, InstanceTypes                |

**Why OpenShift is better:** Multi-tenancy is a core Kubernetes feature. You map teams to projects, bind roles once, and apply the same boundaries to pods and VMs. Identity integrates with enterprise IdPs the same way as the rest of OpenShift ([Identity Providers](../configure-the-cluster/configuring-identity-providers.md)).

### Monitoring and observability

| VMware                     | OpenShift Virtualization                                                                                                                                                                  |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| vRealize / Aria Operations | Platform [Monitoring](../configure-the-cluster/monitoring.md), [Logging](../configure-the-cluster/logging.md), [Network Observability](../configure-the-cluster/network-observability.md) |

**Why OpenShift is better:** Metrics, alerts, and flow data live in the same observability stack as the cluster. You do not maintain a parallel Aria deployment just for VMs, and VM health correlates naturally with node and storage metrics.

---

## Capability mapping checklist

Use this during discovery workshops. For each VMware feature in use, confirm the OpenShift path and owner.

| #  | VMware feature in use        | OpenShift Virtualization path                  | Status |
| -- | ---------------------------- | ---------------------------------------------- | ------ |
| 1  | vSphere HA                   | Workload Availability + live migrate / restart | ☐      |
| 2  | vMotion                      | Live migration + RWX storage                   | ☐      |
| 3  | DRS affinity                 | Affinity / topology / descheduler              | ☐      |
| 4  | NSX-T DFW / microseg         | NetworkPolicy / MultiNetworkPolicy             | ☐      |
| 5  | NSX / AVI LB                 | Service / Route / MetalLB                      | ☐      |
| 6  | vSAN / datastore policies    | StorageClass + CSI                             | ☐      |
| 7  | Content Library              | Templates / DataVolumes                        | ☐      |
| 8  | Backup (VADP / Veeam / etc.) | OADP + VolumeSnapshots                         | ☐      |
| 9  | PowerCLI automation          | GitOps / `oc` / Ansible                        | ☐      |
| 10 | vCenter RBAC                 | Projects + RBAC                                | ☐      |
| 11 | Aria monitoring              | Monitoring + Logging + NetObserv               | ☐      |
| 12 | VM migration factory         | MTV (cold / warm / OVA)                        | ☐      |

---

## Where to go next in this POC

| Goal                                | Doc                                                                                                                                                               |
| ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Install virtualization              | [OpenShift Virtualization](../configure-the-cluster/virtualization.md)                                                                                            |
| Migrate VMs from vSphere            | [Migration Toolkit for Virtualization](../configure-the-cluster/mtv.md)                                                                                           |
| Replace NSX-style microsegmentation | [Network Policy and Microsegmentation](../configure-the-cluster/network-policy.md)                                                                                |
| Node failure / failover behavior    | [Workload Availability](../configure-the-cluster/workload-availability.md), [VM Failover Test](../workloads-and-operations/operational-validation/vm-failover.md) |
| Backup and restore VMs              | [OADP](../configure-the-cluster/oadp.md), [VM Backup and Restore](../workloads-and-operations/operational-validation/vm-backup-restore.md)                        |
| Run a sample VM                     | [RHEL VM with Apache httpd](../workloads-and-operations/virtual-machine-workloads/rhel-httpd-vm.md)                                                               |
| Import an OVA appliance             | [Virtual Appliances (OVA)](../workloads-and-operations/virtual-machine-workloads/ova-virtual-appliance.md)                                                        |
