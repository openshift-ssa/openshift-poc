# Agent Based Installation

The agent-based installer is ideal for bare metal and disconnected environments. It produces a bootable ISO that includes everything needed to install OpenShift without requiring external infrastructure services like DHCP or PXE.

## Steps

1. Create `install-config.yaml` and `agent-config.yaml`
2. Generate the agent ISO
3. Boot all nodes from the ISO
4. Monitor installation progress

```bash
openshift-install agent create image --dir ~/ocp-install
```

Boot all nodes from the generated ISO:

```
~/ocp-install/agent.x86_64.iso
```

Monitor installation:

```bash
openshift-install agent wait-for bootstrap-complete --dir ~/ocp-install --log-level=info
openshift-install agent wait-for install-complete --dir ~/ocp-install --log-level=info
```

---

## Details

### agent-config.yaml

The agent config defines node-level networking with static IPs:

```yaml
apiVersion: v1alpha1
metadata:
  name: <cluster_name>
rendezvousIP: 10.0.0.10
hosts:
  - hostname: control-plane-0
    role: master
    interfaces:
      - name: eno1
        macAddress: aa:bb:cc:dd:ee:00
    networkConfig:
      interfaces:
        - name: eno1
          type: ethernet
          state: up
          ipv4:
            enabled: true
            address:
              - ip: 10.0.0.10
                prefix-length: 24
            dhcp: false
      dns-resolver:
        config:
          server:
            - 1.1.1.1
      routes:
        config:
          - destination: 0.0.0.0/0
            next-hop-address: 10.0.0.1
            next-hop-interface: eno1
  - hostname: control-plane-1
    role: master
    interfaces:
      - name: eno1
        macAddress: aa:bb:cc:dd:ee:01
    networkConfig:
      interfaces:
        - name: eno1
          type: ethernet
          state: up
          ipv4:
            enabled: true
            address:
              - ip: 10.0.0.11
                prefix-length: 24
            dhcp: false
      dns-resolver:
        config:
          server:
            - 1.1.1.1
      routes:
        config:
          - destination: 0.0.0.0/0
            next-hop-address: 10.0.0.1
            next-hop-interface: eno1
  - hostname: control-plane-2
    role: master
    interfaces:
      - name: eno1
        macAddress: aa:bb:cc:dd:ee:02
    networkConfig:
      interfaces:
        - name: eno1
          type: ethernet
          state: up
          ipv4:
            enabled: true
            address:
              - ip: 10.0.0.12
                prefix-length: 24
            dhcp: false
      dns-resolver:
        config:
          server:
            - 1.1.1.1
      routes:
        config:
          - destination: 0.0.0.0/0
            next-hop-address: 10.0.0.1
            next-hop-interface: eno1
```

### Rendezvous IP

The `rendezvousIP` is the IP address of the node that acts as the temporary bootstrap host. This node coordinates the installation of all other nodes. It must be one of the control plane nodes.

### Disconnected Environments

For air-gapped installations, mirror the OpenShift release images to a local registry:

```bash
oc adm release mirror \
  --from=quay.io/openshift-release-dev/ocp-release:4.17.0-x86_64 \
  --to=registry.example.com:5000/ocp4/openshift4 \
  --to-release-image=registry.example.com:5000/ocp4/openshift4:4.17.0-x86_64
```

Add the mirror registry to `install-config.yaml`:

```yaml
imageContentSources:
  - mirrors:
      - registry.example.com:5000/ocp4/openshift4
    source: quay.io/openshift-release-dev/ocp-release
  - mirrors:
      - registry.example.com:5000/ocp4/openshift4
    source: quay.io/openshift-release-dev/ocp-v4.0-art-dev
```

### Advantages of Agent-Based Install

- No PXE/DHCP infrastructure required
- Static IP configuration built into the ISO
- Single bootable artifact for all nodes
- Well-suited for disconnected and bare metal environments
