# Post-Installation Overview

After the OpenShift cluster is installed, complete the following operations to prepare it for production workloads.

## Recommended Order

Install and configure in this order to avoid dependency issues:

1. **Kubernetes NMState Operator** — Install first if you need advanced networking (bonds, VLANs, OVS bridges)
2. **[Storage](storage.md)** — Install your CSI driver and create StorageClasses
3. **[Registry](registry.md)** — Configure persistent storage for the internal image registry
4. **[OpenShift GitOps](openshift-gitops.md)** — Install ArgoCD for GitOps workflows
5. **[External Secrets Operator](external-secrets-operator.md)** — Integrate external secret management
6. **[Workload Availability](workload-availability.md)** — Node health checks and automatic remediation
7. **[Virtualization](virtualization.md)** — OpenShift Virtualization (after workload availability)
8. **[POC Banner](poc-banner.md)** — Mark the UI as a PoC environment

## Operations

- [Add Worker Node](add-worker-node.md) - Add a worker node to an existing cluster
- [Rotate SSH Keys](rotate-ssh-keys.md) - Rotate SSH keys on cluster nodes
- [Machine Config](machine-config.md) - Create machine configuration files

## Networking

- [Networking](networking.md) - NNCPs, OVS bridges, CUDNs, and underlay networking

## Documentation

- [Post Install Configuration](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html-single/postinstallation_configuration/index)
- [Installing on Bare Metal](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html-single/installing_on_bare_metal/index)
- [Configuring Firewall](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/installation_configuration/configuring-firewall)
- [Agent-Based Installer](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html-single/installing_an_on-premise_cluster_with_the_agent-based_installer/index)
