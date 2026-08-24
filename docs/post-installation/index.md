# Configure the Cluster

[Post-installation configuration](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html-single/postinstallation_configuration/index)

After the cluster is installed, complete the following to prepare it for workloads. Items are grouped by purpose — complete the **Required** section first, then add capabilities based on your POC scope.

## Required

These must be completed before deploying any workloads:

1. **[NMState Operator](nmstate.md)** — Required for advanced networking (bonds, VLANs, OVS bridges)
2. **[Storage](storage/index.md)** — Install your CSI driver and create StorageClasses
3. **[Registry](registry.md)** — Configure persistent storage for the internal image registry

You can run workloads with `kubeadmin` at this point. Configure an [identity provider](configuring-identity-providers.md) before demo day, and keep `kubeadmin` until at least one IdP user has `cluster-admin`.

## Workload Availability

Install this **before** Virtualization if you will test node-loss or live migration:

- [Descheduler & Affinity](workload-availability.md) — Node health checks, automatic remediation, and workload rebalancing
- [OADP (Backup & Restore)](oadp.md) — Backup and restore for applications and virtual machines

## Virtualization & Migration

Run and migrate virtual machines on OpenShift:

- [OpenShift Virtualization](virtualization.md) — Install and configure KubeVirt for running VMs
- [Migration Toolkit for Virtualization](mtv.md) — Migrate VMs from VMware vSphere, RHV, or OpenStack

## Observability

Centralized logging, metrics, and network visibility:

- [Logging](logging.md) — Log collection and storage with Loki and OpenShift Logging
- [Network Observability](network-observability.md) — eBPF flow collection, topology, and Network Traffic console
- [MultiCluster Observability](multicluster-observability.md) — Centralized monitoring across managed clusters (fleet management only)

## Optional

Install based on your POC scope:

- [Identity Providers](configuring-identity-providers.md) — LDAP, OIDC, or other authentication (recommended before demo day)
- [Networking](networking.md) — NNCPs, OVS bridges, CUDNs, and underlay networking
- [OpenShift GitOps](openshift-gitops.md) — ArgoCD for GitOps workflows
- [External Secrets Operator](external-secrets-operator.md) — Integrate external secret management (Vault, AWS, etc.)
- [Service Mesh](service-mesh.md) — Istio ambient mode (out of POC baseline unless explicitly in scope)
- [Web Terminal](web-terminal.md) — Embedded CLI terminal in the web console
- [Operators from Artifactory](operators-from-artifactory.md) — Install operators from a private Artifactory registry
- [POC Banner](poc-banner.md) — Mark the web console as a POC environment
