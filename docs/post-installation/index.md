# Post-Installation Overview

[Post Install Configuration](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html-single/postinstallation_configuration/index)

After the OpenShift cluster is installed, complete the following operations to prepare it for workloads.

## Required

These must be completed in order before deploying any workloads:

1. **[NMState Operator](nmstate.md)** — Required for advanced networking (bonds, VLANs, OVS bridges)
2. **[Storage](storage.md)** — Install your CSI driver and create StorageClasses
3. **[Registry](registry.md)** — Configure persistent storage for the internal image registry

## Optional

These are modular and can be installed in any order based on your needs but we usually recommend this order. 

- [Networking](networking.md) — NNCPs, OVS bridges, CUDNs, and underlay networking
- [External Secrets Operator](external-secrets-operator.md) — Integrate external secret management
- [Workload Availability](workload-availability.md) — Node health checks and automatic remediation
- [Node Maintenance Operator](node-maintenance-operator.md) — Place nodes in maintenance mode by cordoning and draining
- [Virtualization](virtualization.md) — OpenShift Virtualization (requires workload availability first)
- [Migration Toolkit for Virtualization](mtv.md) — Migrate VMs from vSphere, RHV, or OpenStack
- [OADP](oadp.md) — Backup and restore for applications and virtual machines
- [Service Mesh](service-mesh.md) — Istio ambient mode (sidecar-less mTLS and traffic management)
- [OpenShift GitOps](openshift-gitops.md) — ArgoCD for GitOps workflows
- [MultiCluster Observability](multicluster-observability.md) — Centralized monitoring across managed clusters
- [Identity Providers](configuring-identity-providers.md) — Configure LDAP, OIDC, or other authentication
- [POC Banner](poc-banner.md) — Mark the UI as a PoC environment
