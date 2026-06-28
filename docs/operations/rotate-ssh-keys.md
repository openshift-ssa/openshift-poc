# Rotate SSH Keys

[Machine Config Operator Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/machine_configuration/machine-configs-configure#machineconfig-modify-journald_machine-configs-configure)

!!! note
    After applying the MachineConfig, the Machine Config Operator will roll out the change to each node, causing a rolling reboot. Ensure your cluster has sufficient capacity to handle node drains during this process.

## Steps

1. Generate a new key:

  ```bash
  ssh-keygen -t ed25519 -f ~/.ssh/ocp -C "ocp-key-rotation"
  ```

2. Export the existing MachineConfig:

  ```bash
  oc get machineconfig 99-master-ssh -o yaml > 99-master-ssh.yaml
  ```

3. Edit to include both the old and new keys:

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

4. Apply:

  ```bash
  oc apply -f 99-master-ssh.yaml
  ```

5. Repeat for Worker Nodes using `99-worker-ssh` instead of `99-master-ssh`

6. Once all nodes have rebooted and are Ready, verify SSH access with the new key:

  ```bash
  ssh -i ~/.ssh/ocp core@{{ node_ip }}
  ```

7. After confirming the new key works, remove the old key from the MachineConfig and reapply
