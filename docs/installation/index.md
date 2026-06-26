# Installation Overview

OpenShift supports multiple installation methods for on-premise environments. Choose the method that best fits your infrastructure and operational requirements.

## Installation Methods

| Method                                      | Best For                                          | Automation Level |
| ------------------------------------------- | ------------------------------------------------- | ---------------- |
| [Installer Provisioned (IPI)](ipi.md)       | vSphere, automated provisioning                   | High             |
| [User Provisioned (UPI)](upi.md)            | Custom infrastructure, maximum control            | Low              |
| [Agent Based](agent-based.md)               | Bare metal, disconnected, no external services    | Medium           |

## Common Preparation

Regardless of installation method, you need the following.

```bash
mkdir ~/ocp-install && cd ~/ocp-install
```

Create the `install-config.yaml`:

```yaml
apiVersion: v1
metadata:
  name: <cluster_name>
baseDomain: <base_domain>
compute:
  - name: worker
    replicas: 3
controlPlane:
  name: control-plane
  replicas: 3
networking:
  networkType: OVNKubernetes
  clusterNetwork:
    - cidr: 10.128.0.0/14
      hostPrefix: 23
  serviceNetwork:
    - 172.30.0.0/16
  machineNetwork:
    - cidr: 10.0.0.0/24
platform:
  none: {}
pullSecret: '<pull_secret_contents>'
sshKey: '<ssh_public_key>'
```

---

## Details

### Pull Secret

Obtain your pull secret from [console.redhat.com](https://console.redhat.com/openshift/install/pull-secret). Store it securely:

```bash
cp ~/pull-secret.json ~/.pull-secret
chmod 600 ~/.pull-secret
```

### SSH Key

Generate an SSH key pair for node access:

```bash
ssh-keygen -t ed25519 -N '' -f ~/.ssh/ocp-key
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/ocp-key
```

### Backup install-config.yaml

The installer consumes and deletes `install-config.yaml` during installation. Always make a backup:

```bash
cp install-config.yaml install-config.yaml.bak
```
