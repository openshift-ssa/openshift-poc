# Other Installation Methods

These are alternative installation methods for specific use cases. For most POCs, use the [Assisted Installer](../assisted-installer.md) or the [Agent-Based Installer](../agent-based.md) instead.

## Hub and Spoke

Multi-cluster management with Advanced Cluster Management (ACM). A Single Node OpenShift (SNO) hub provisions and manages spoke clusters. See [Hub and Spoke](hub-and-spoke.md).

## VMware vSphere IPI

Installer-Provisioned Infrastructure on VMware vSphere. See [VMware vSphere IPI](vmware-install.md).

## OpenShift on OpenShift

Nested clusters with hosted control planes running as pods. See [OpenShift on OpenShift](openshift-on-openshift.md).

## Disconnected Environments

For environments where cluster nodes cannot reach the internet. Set up a mirror registry or pull-through cache, then configure OpenShift to use it. See [Disconnected](disconnected.md).
