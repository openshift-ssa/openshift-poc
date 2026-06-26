# Prerequisites Overview

Before beginning an OpenShift installation, ensure all infrastructure, networking, DNS, load balancing, and storage requirements are met.

## Checklist

- [ ] [Infrastructure](infrastructure.md) - Compute resources provisioned
- [ ] [Networking](networking.md) - Network topology and firewall rules configured
- [ ] [DNS](dns.md) - Required DNS records created
- [ ] [Load Balancer](load-balancer.md) - API and Ingress load balancers configured
- [ ] [Storage](storage.md) - Persistent storage backend available

## Installer Machine

The machine used to run the OpenShift installer requires the following.

```bash
sudo dnf install -y podman openssl jq
```

Download the OpenShift installer and CLI tools:

```bash
OCP_VERSION="stable"
curl -sL https://mirror.openshift.com/pub/openshift-v4/clients/ocp/${OCP_VERSION}/openshift-install-linux.tar.gz | tar xzf - -C /usr/local/bin/
curl -sL https://mirror.openshift.com/pub/openshift-v4/clients/ocp/${OCP_VERSION}/openshift-client-linux.tar.gz | tar xzf - -C /usr/local/bin/
```

Verify the tools are installed:

```bash
openshift-install version
oc version --client
```

---

## Details

### Installer Machine Requirements

The installer machine does not need to be part of the cluster. It is used to generate ignition configs, run the installer, and interact with the cluster via `oc`. It requires:

- RHEL 8+ or Fedora (latest stable)
- 4 vCPU, 8 GB RAM minimum
- Internet access (or access to a mirror registry for disconnected installs)
- The pull secret from [console.redhat.com](https://console.redhat.com/openshift/install/pull-secret)
