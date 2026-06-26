# Cluster Agent-Based Install

This guide covers the agent-based installation for a standalone multi-node cluster. This should all be done from the installation host.

## Create the Configurations

The agent-based install requires two configuration files:

- `install-config.yaml` — cluster-level information
- `agent-config.yaml` — host-level configurations

### Create the Working Directory

```bash
mkdir -p ocp && cd ocp
git init
echo "install/" > .gitignore
echo "# POC install notes" > notes.md
touch install-config.yaml
touch agent-config.yaml
git add -A
git commit -m "repo initialized"
```

### Create the Install Config

```yaml
apiVersion: v1
baseDomain: ocp.basedomain.com
metadata:
  name: poc
controlPlane:
  name: master
  architecture: amd64
  hyperthreading: Enabled
  replicas: 3
compute:
- name: worker
  architecture: amd64
  hyperthreading: Enabled
  replicas: 3
networking:
  clusterNetwork:
  - cidr: 10.128.0.0/14
    hostPrefix: 23
  machineNetwork:
  - cidr: 10.0.0.0/28
  networkType: OVNKubernetes
  serviceNetwork:
  - 172.30.0.0/16
platform:
  baremetal:
    apiVIP: 10.0.0.2
    ingressVIP: 10.0.0.3
    additionalNTPServers:
      - 0.us.pool.ntp.org
      - 1.us.pool.ntp.org
pullSecret: 'value from ~/pull-secret.txt'
sshKey: 'value from ~/.ssh/ocp.pub'
```

If your environment requires a proxy, append to the end of `install-config.yaml`:

```yaml
proxy:
  httpProxy: http://user:password@proxy.example.com:3128
  httpsProxy: http://user:password@proxy.example.com:3128
  noProxy: basedomain.com,localhost,127.0.0.1,.cluster.local,.svc,10.0.0.0/8,192.168.0.0/16,172.16.0.0/12,{{ node_subnet }},{{ api_vip }},{{ ingress_vip }}
```

If your environment uses a MITM proxy, add the trust bundle:

```yaml
additionalTrustBundlePolicy: Always
additionalTrustBundle: |
    -----BEGIN CERTIFICATE-----
  MIIDzTCCArWgAwIBAgIUXXXXXXXXXXXXXXXXXXXXXXXXXXXwDQYJKoZIhvcNAQEL
  ...
  -----END CERTIFICATE-----
```

### Create the Agent Config

The `agent-config.yaml` is a list of hosts' information. Below is an example with two ethernet connections bonded together in an LACP bond with a VLAN.

```yaml
apiVersion: v1alpha1
kind: AgentConfig
metadata:
  name: poc
rendezvousIP: 10.0.0.4
additionalNtpSources:
  - 0.us.pool.ntp.org
  - 1.us.pool.ntp.org
hosts:
  - hostname: ocp-poc-cp-01
    role: master
    rootDeviceHints:
      deviceName: "/dev/sda"
    interfaces:
      - name: eno1
        macAddress: A1:B2:3C:4D:1E:11
      - name: eno2
        macAddress: A1:B2:3C:4D:2E:11
    networkConfig:
      interfaces:
        - name: bond0
          type: bond
          state: up
          link-aggregation:
            mode: 802.3ad
            port:
              - eno1
              - eno2
            options:
              miimon: "100"
              lacp_rate: fast
          ipv4:
            enabled: false
          ipv6:
            enabled: false
        - name: bond0.3
          type: vlan
          state: up
          vlan:
            base-iface: bond0
            id: 3
          ipv4:
            enabled: true
            address:
              - ip: 10.0.0.4
                prefix-length: 28
            dhcp: false
          ipv6:
            enabled: false
      dns-resolver:
        config:
          server:
            - dns1.basedomain.com
            - dns2.basedomain.com
      routes:
        config:
          - destination: 0.0.0.0/0
            next-hop-address: 10.0.0.1
            next-hop-interface: bond0.3
            table-id: 254
```

Repeat the host entry for each control plane and worker node, updating hostname, MAC addresses, IP addresses, and role (`master` or `worker`).

!!! note
    Notice the inconsistent labels and spellings in the OpenShift configs: `macAddress` in the interfaces stanza, but `mac-address` in the networkConfig stanza. `additionalNtpSources` is used in agent-config, but `additionalNTPServers` in install-config.

### Agent Config with Active-Backup Bond (no VLAN)

If your environment uses active-backup bonding instead of LACP:

```yaml
    networkConfig:
      interfaces:
        - name: eno1
          type: ethernet
          state: up
          mac-address: A1:B2:3C:4D:1E:11
          ipv4:
            enabled: false
          ipv6:
            enabled: false
        - name: eno2
          type: ethernet
          state: up
          mac-address: A1:B2:3C:4D:2E:11
          ipv4:
            enabled: false
          ipv6:
            enabled: false
        - name: bond0
          type: bond
          state: up
          ipv4:
            enabled: true
            address:
              - ip: 10.0.0.4
                prefix-length: 28
            dhcp: false
          link-aggregation:
            mode: active-backup
            port:
              - eno1
              - eno2
            options:
              miimon: '100'
              primary: eno1
          ipv6:
            enabled: false
      dns-resolver:
        config:
          server:
            - 10.0.0.2
      routes:
        config:
          - destination: 0.0.0.0/0
            next-hop-address: 10.0.0.1
            next-hop-interface: bond0
            table-id: 254
```

### Compact 3-Node Cluster (No Workers)

For a compact cluster where control plane nodes are schedulable and also run workloads, set `compute[0].replicas` to `0` in `install-config.yaml`. The three control plane nodes will handle both control plane and worker duties.

### Cluster Manifests

If you have additional manifests to apply at install time (e.g., MachineConfigs, NMState configs), place them in a folder named `cluster-manifests` at the same level as `install-config.yaml` and `agent-config.yaml`.

```bash
mkdir -p ocp/cluster-manifests
# Add any manifests to apply during installation
```

## Generate the ISO

Create a script `create-iso.sh` in your working directory:

```bash
#!/bin/bash
rm -rf install
mkdir install
cp -r install-config.yaml agent-config.yaml cluster-manifests install
openshift-install agent create image --dir=install --log-level=debug
```

```bash
chmod +x create-iso.sh
./create-iso.sh
```

This generates `install/agent.x86_64.iso`.

## Host the ISO

Serve the ISO from the installation host using Podman:

```bash
podman run -d --name iso-http \
  -p 8080:8080 \
  -v ~/ocp/install/agent.x86_64.iso:/var/www/html/agent.x86_64.iso:Z \
  registry.redhat.io/rhel9/httpd-24:9.6
```

Verify the ISO is accessible:

```bash
wget http://{{ installation_host }}:8080/agent.x86_64.iso
```

## Boot and Install

Mount the ISO on each node via BMC virtual media (Redfish, iLO, iDRAC) and boot. When all hosts are booted, monitor the install:

```bash
openshift-install agent wait-for bootstrap-complete --dir=install
openshift-install agent wait-for install-complete --dir=install
```

At the end of the process, you will be presented with the URL for the cluster endpoint along with the kubeadmin credentials. They are also available in the `install` folder as `kubeadmin-password` and `auth/kubeconfig`.

## Validate the Install

```bash
oc login --server=https://api.poc.ocp.basedomain.com:6443 -u kubeadmin -p {{ password }}
oc get nodes
oc get clusterversion
oc get clusteroperators
```

Test container image pull connectivity:

```bash
oc debug node/{{ worker_node_name }} -- chroot /host \
  podman pull registry.redhat.io/ubi9/ubi:latest
```

Cleanup leftover pods:

```bash
oc delete pods --all-namespaces --field-selector=status.phase=Succeeded
oc delete pods --all-namespaces --field-selector=status.phase=Failed
```

For troubleshooting, see [Troubleshooting](troubleshooting.md).
