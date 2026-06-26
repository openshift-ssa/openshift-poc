# Rotate SSH Keys

## Generate a New Key

```bash
ssh-keygen -t ed25519 -f ~/.ssh/new_ocp_key -C "ocp-key-rotation"
```

## Update the MachineConfig

Export the existing MachineConfig:

```bash
oc get machineconfig 99-master-ssh -o yaml > 99-master-ssh.yaml
```

Edit to include both the old and new keys:

```yaml
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfig
metadata:
  labels:
    machineconfiguration.openshift.io/role: master
  name: 99-master-ssh
spec:
  config:
    ignition:
      version: 3.2.0
    passwd:
      users:
      - name: core
        sshAuthorizedKeys:
        - ssh-ed25519 AAAA...your_old_key_here...
        - ssh-ed25519 AAAA...your_new_key_here...
```

Apply:

```bash
oc apply -f 99-master-ssh.yaml
```

## Repeat for Worker Nodes

Repeat using `99-worker-ssh` instead of `99-master-ssh`.

!!! note
    After applying the MachineConfig, the Machine Config Operator will roll out the change to each node, causing a rolling reboot. Ensure your cluster has sufficient capacity to handle node drains during this process.
