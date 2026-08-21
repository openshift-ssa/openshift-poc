# Configure the Cluster

[Post-installation configuration](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html-single/postinstallation_configuration/index)

After the cluster is installed, complete the following to prepare it for workloads. Items are grouped by purpose — complete the **Required** section first, then add capabilities based on your POC scope.

## Required

These must be completed before deploying any workloads:

1. **[NMState Operator](nmstate.md)** — Required for advanced networking (bonds, VLANs, OVS bridges)
2. **[Storage](storage/index.md)** — Install your CSI driver and create StorageClasses
3. **[Registry](registry.md)** — Configure persistent storage for the internal image registry
4. **[Identity Providers](configuring-identity-providers.md)** — Configure LDAP, OIDC, or other authentication

## Observability

Centralized logging, metrics, and network visibility:

- [Logging](logging.md) — Log collection and storage with Loki and OpenShift Logging
- [Network Observability](network-observability.md) — eBPF flow collection, topology, and Network Traffic console
- [MultiCluster Observability](multicluster-observability.md) — Centralized monitoring across managed clusters (fleet management only)

## Virtualization & Migration

Run and migrate virtual machines on OpenShift:

- [OpenShift Virtualization](virtualization.md) — Install and configure KubeVirt for running VMs
- [Migration Toolkit for Virtualization](mtv.md) — Migrate VMs from VMware vSphere, RHV, or OpenStack

## Workload Availability

High availability and data protection:

- [Descheduler & Affinity](workload-availability.md) — Node health checks, automatic remediation, and workload rebalancing
- [OADP (Backup & Restore)](oadp.md) — Backup and restore for applications and virtual machines

## Optional

Install based on your POC scope:

- [Networking](networking.md) — NNCPs, OVS bridges, CUDNs, and underlay networking
- [OpenShift GitOps](openshift-gitops.md) — ArgoCD for GitOps workflows
- [External Secrets Operator](external-secrets-operator.md) — Integrate external secret management (Vault, AWS, etc.)
- [Service Mesh](service-mesh.md) — Istio ambient mode (sidecar-less mTLS and traffic management)
- [Web Terminal](web-terminal.md) — Embedded CLI terminal in the web console
- [Operators from Artifactory](operators-from-artifactory.md) — Install operators from a private Artifactory registry
- [POC Banner](poc-banner.md) — Mark the web console as a POC environment
