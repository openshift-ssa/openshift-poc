# Prerequisites Overview

Before beginning an OpenShift installation, ensure all infrastructure, networking, DNS, load balancing, and storage requirements are met. These prerequisites apply to both the [Standalone Cluster](../standalone/index.md) and [Fleet Management](../fleet-management/index.md) approaches.

Here are some assumptions: 

- Installing on bare metal in an on-premise environment
- Networking is all static - no DHCP
- Storage will be handled by third-party vendor with a supported CSI driver

## Checklist

- [ ] [Infrastructure](infrastructure.md) - Compute resources provisioned
- [ ] [Networking](networking.md) - Network topology and firewall rules configured
- [ ] [DNS](dns.md) - Required DNS records created
- [ ] [Load Balancer](load-balancer.md) - API and Ingress load balancers configured (multi-node only)
- [ ] [Storage](storage.md) - Persistent storage backend available

## Installer Machine

The machine used to download the discovery ISO and interact with the cluster requires the following.

```bash
sudo dnf install -y openssl jq
```

Download the OpenShift CLI:

```bash
OCP_VERSION="stable"
curl -sL https://mirror.openshift.com/pub/openshift-v4/clients/ocp/${OCP_VERSION}/openshift-client-linux.tar.gz | tar xzf - -C /usr/local/bin/
```

Verify the CLI is installed:

```bash
oc version --client
```

---

## Details

### Installer Machine Requirements

The installer machine does not need to be part of the cluster. It is used to interact with the cluster via `oc` after installation. It requires:

- RHEL 8+ or Fedora (latest stable)
- Internet access to reach [console.redhat.com](https://console.redhat.com)
- A Red Hat account with an active OpenShift subscription or evaluation

### Red Hat Account

You need a Red Hat account to access the Assisted Installer. If you do not have one, create an account at [console.redhat.com](https://console.redhat.com). Your pull secret is automatically managed when using the Assisted Installer.
