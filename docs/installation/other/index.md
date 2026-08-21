# Other Installation Methods

## Disconnected / Air-Gapped Environments

For environments where cluster nodes cannot reach the internet, a disconnected installation is a two-step process:

**Step 1 — Set up the internal registry** (choose one):

- [Mirror Registry with oc-mirror](disconnected-oc-mirror.md) — Fully air-gapped; pre-stage all content into a local registry
- [Pull-Through Cache (Artifactory / Nexus)](disconnected-pull-through-cache.md) — Cache with outbound access proxies images on demand

**Step 2 — Configure OpenShift to use it:**

- [Configuring OpenShift for a Disconnected Registry](disconnected-openshift-config.md) — `install-config.yaml` setup, operator configuration, upgrades, and verification

## Other Methods

- [VMware vSphere IPI](vmware-install.md) — Installer-Provisioned Infrastructure on VMware vSphere
- [OpenShift on OpenShift (Hosted Control Planes)](openshift-on-openshift.md) — Nested clusters with control planes running as pods
- [Fleet Management](fleet-management/index.md) — Multi-cluster management with ACM, including hub install and bare metal provisioning

---

For the primary POC installation methods, see the [Installation Overview](../index.md).
