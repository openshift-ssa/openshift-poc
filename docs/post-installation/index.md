# Post-Installation Overview

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
- [Virtualization](virtualization.md) — OpenShift Virtualization (requires workload availability first)
- [OADP](oadp.md) — Backup and restore for applications and virtual machines
- [OpenShift GitOps](openshift-gitops.md) — ArgoCD for GitOps workflows
- [MultiCluster Observability](multicluster-observability.md) — Centralized monitoring across managed clusters
- [POC Banner](poc-banner.md) — Mark the UI as a PoC environment

## Documentation

- [Post Install Configuration](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html-single/postinstallation_configuration/index)
- [Installing on Bare Metal](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html-single/installing_on_bare_metal/index)
- [Configuring Firewall](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/installation_configuration/configuring-firewall)
- [Assisted Installer](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html-single/installing_with_the_assisted_installer/index)
