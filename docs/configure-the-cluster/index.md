# Configure the Cluster

[Post-installation configuration](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html-single/postinstallation_configuration/index)

After the cluster is installed, complete storage and registry configuration before running workloads. Networking day-2 steps depend on your topology:

1. **[NMState Operator](./nmstate.md)** — Required when you need bonds, VLANs, or OVS bridges after install (skip if install-time static networking / single NIC is enough)
2. **[Configure Networking](./networking.md)** — NNCPs, OVS bridges, CUDNs, and underlay networking (when using NMState)
3. **[Storage](./storage/index.md)** — Install your CSI driver and create StorageClasses
4. **[Registry](./registry.md)** — Configure persistent storage for the internal image registry

## Additional Configuration

### OpenShift Virtualization
- [Workload Availability](./workload-availability.md) — Node health checks, automatic remediation, and workload rebalancing
- [OpenShift Virtualization](./virtualization.md) — Install and configure KubeVirt for running VMs
- [Migration Toolkit for Virtualization](./mtv.md) — Migrate VMs from VMware vSphere, RHV, or OpenStack
- [OADP (Backup & Restore)](./oadp.md) — Backup and restore for applications and virtual machines

### Observability
- [Monitoring and Alerting](./monitoring.md) — Built-in Prometheus stack, user workload monitoring, and Alertmanager
- [Logging](./logging.md) — Log collection and storage with Loki and OpenShift Logging
- [Network Observability](./network-observability.md) — eBPF flow collection, topology, and Network Traffic console
- [MultiCluster Observability](./multicluster-observability.md) — Centralized monitoring across managed clusters (fleet management only)

### IDM and Operations
- [Identity Providers](./configuring-identity-providers.md) — LDAP, OIDC, or other authentication (recommended before demo day)
- [OpenShift GitOps](./openshift-gitops.md) — ArgoCD for GitOps workflows
- [External Secrets Operator](./external-secrets-operator.md) — Integrate external secret management (Vault, AWS, etc.)
- [Service Mesh](./service-mesh.md) — Istio ambient mode (out of POC baseline unless explicitly in scope)
- [Operators from Artifactory](./operators-from-artifactory.md) — Install operators from a private Artifactory registry

### Other Tools
- [Web Terminal](./web-terminal.md) — Embedded CLI terminal in the web console
- [POC Banner](./poc-banner.md) — Mark the web console as a POC environment
