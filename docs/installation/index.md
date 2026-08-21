# Install the Cluster

For a POC, there are two primary installation methods:

- **[Assisted Installer](assisted-installer.md)** — Web-based, guided installation via the Red Hat Hybrid Cloud Console. Best for organizations who want a straightforward setup without deep CLI expertise.
- **[Agent-Based Installer](agent-based.md)** — Fully CLI-driven bare metal installation using a bootable ISO. Best for environments with strict network controls or no cloud console access.

Both methods produce an identical cluster. Choose based on your environment's connectivity and operational preferences.

## Disconnected Environments

If your cluster nodes cannot reach the internet, you need to set up an internal registry first:

1. **Set up the registry** — choose one:
    - [Mirror Registry (oc-mirror)](disconnected/oc-mirror.md) — fully air-gapped, pre-stage all content
    - [Pull-Through Cache](disconnected/pull-through-cache.md) — artifact repo proxies images on demand
2. **[Configure OpenShift](disconnected/openshift-config.md)** — point `install-config.yaml` and operators at the registry

## Other Methods

For VMware, hosted control planes, or fleet management, see [Other Methods](other/index.md).

## Troubleshooting

For common issues during installation, see [Troubleshooting](troubleshooting.md).
