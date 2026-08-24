# Other Installation Methods

These are alternative installation methods for specific use cases:

- [VMware vSphere IPI](vmware-install.md) — Installer-Provisioned Infrastructure on VMware vSphere
- [OpenShift on OpenShift (Hosted Control Planes)](openshift-on-openshift.md) — Nested clusters with control planes running as pods
- [Fleet Management](fleet-management/index.md) — Multi-cluster management with ACM, including hub install and bare metal provisioning

## Disconnected environments

Disconnected install is a two-step process. Set up a registry, then point OpenShift at it:

1. **Set up the registry** (choose one):
    - [Mirror Registry (oc-mirror)](../disconnected/oc-mirror.md) — fully air-gapped
    - [Pull-Through Cache](../disconnected/pull-through-cache.md) — Artifactory or Nexus with outbound access
2. **[Configure OpenShift](../disconnected/openshift-config.md)** — `install-config.yaml`, catalog sources, and operators

For the primary POC installation methods, see the [Installation Overview](../index.md).
