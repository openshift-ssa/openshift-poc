# Post-Installation Overview

After the OpenShift cluster is installed, complete the following day 2 operations to prepare it for production workloads.

## Checklist

- [ ] [Day 2 Operations](day2.md) - Configure authentication, storage, monitoring, and GitOps

## Verify Cluster Health

```bash
export KUBECONFIG=~/ocp-poc/auth/kubeconfig
oc get nodes
oc get clusteroperators
oc get clusterversion
```

All nodes should be in `Ready` status and all cluster operators should be `Available=True`.

---

## Details

### kubeadmin Credentials

The installer creates a temporary `kubeadmin` user. After installation, the password is available in the Assisted Installer UI or downloaded with the kubeconfig.

Access the web console:

```bash
oc whoami --show-console
```

!!! warning
    Remove the `kubeadmin` user after configuring an identity provider. The kubeadmin account is intended for initial setup only.
