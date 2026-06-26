# Machine Config

## Creating a Machine Configuration File

Base64 encode content for inclusion in a MachineConfig:

```bash
echo -n "mysecretvalue" | base64
```

Then place the encoded value after `base64,` in the MachineConfig:

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

## Creating a Machine Configuration File with Butane

Butane transpiles human-readable configs into MachineConfig resources, avoiding manual base64 encoding.

### Install Butane

```bash
curl -LO https://mirror.openshift.com/pub/openshift-v4/clients/butane/latest/butane
chmod +x butane
sudo mv butane /usr/local/bin/
```

### Write a Butane Config

Create `99-worker-example.bu`:

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

### Transpile to MachineConfig

```bash
butane 99-worker-example.bu -o 99-worker-example.yaml
```

### Using a Local File

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

### Apply

```bash
oc apply -f 99-worker-example.yaml
```
