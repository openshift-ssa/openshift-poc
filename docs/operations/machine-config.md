# Machine Config

[Machine Config Operator Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/machine_configuration/index)

## Creating a Machine Configuration File

1. Base64 encode the content for inclusion in a MachineConfig:

  ```bash
  echo -n "mysecretvalue" | base64
  ```

2. Place the encoded value after `base64,` in the MachineConfig:

  ```yaml
  apiVersion: machineconfiguration.openshift.io/v1
  kind: MachineConfig
  metadata:
    name: 99-worker-example
    labels:
      machineconfiguration.openshift.io/role: worker
  spec:
    config:
      ignition:
        version: 3.4.0
      storage:
        files:
        - path: /etc/file.conf
          mode: 0644
          overwrite: true
          contents:
            source: data:text/plain;charset=utf-8;base64,bXlzZWNyZXR2YWx1ZQ==
  ```

3. Apply:

  ```bash
  oc apply -f 99-worker-example.yaml
  ```

## Creating a Machine Configuration File with Butane

Butane transpiles human-readable configs into MachineConfig resources, avoiding manual base64 encoding.

1. Install Butane:

  ```bash
  curl -LO https://mirror.openshift.com/pub/openshift-v4/clients/butane/latest/butane
  chmod +x butane
  sudo mv butane /usr/local/bin/
  ```

2. Write a Butane config — create `99-worker-example.bu`:

  ```yaml
  variant: openshift
  version: latest.0
  metadata:
    name: 99-worker-example
    labels:
      machineconfiguration.openshift.io/role: worker
  storage:
    files:
      - path: /etc/file.conf
        mode: 0644
        overwrite: true
        contents:
          inline: |
            mysecretvalue
  ```

3. Transpile to MachineConfig:

  ```bash
  butane 99-worker-example.bu -o 99-worker-example.yaml
  ```

4. Apply:

  ```bash
  oc apply -f 99-worker-example.yaml
  ```

### Using a Local File

Instead of `inline`, reference a local file:

```yaml
variant: openshift
version: latest.0
metadata:
  name: 99-worker-example
  labels:
    machineconfiguration.openshift.io/role: worker
storage:
  files:
    - path: /etc/file.conf
      mode: 0644
      overwrite: true
      contents:
        local: file.conf
```

```bash
butane 99-worker-example.bu --files-dir . -o 99-worker-example.yaml
```
