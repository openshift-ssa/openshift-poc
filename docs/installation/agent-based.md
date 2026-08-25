# Agent-Based Installer

The agent-based installer is an alternative to the Assisted Installer that generates a bootable ISO locally using `openshift-install`. It is ideal for environments with limited or no connectivity to console.redhat.com, or when you need full control over the installation artifacts.

This guide covers installing a multi-node cluster. All steps should be performed from the installation host.

## Create the Working Directory

```bash
mkdir -p ~/ocp && cd ~/ocp
git init
echo "install/" > .gitignore
echo "# POC install notes" > notes.md
touch install-config.yaml
touch agent-config.yaml
git add -A
git -c user.name="POC Install" -c user.email="poc@localhost" commit -m "repo initialized"
```

## install-config.yaml

The `install-config.yaml` defines cluster-level settings.

```yaml
apiVersion: v1
baseDomain: {{ base_domain }}
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
    apiVIPs:
        - 10.0.0.3
    ingressVIPs:
        - 10.0.0.4
    additionalNTPServers:
      - {{ ntp_server_1 }}
      - {{ ntp_server_2 }}
pullSecret: 'value from ~/pull-secret.txt'
sshKey: 'value from ~/.ssh/ocp.pub'
```

### Proxy Configuration

If your environment requires a proxy, append to the end of `install-config.yaml`:

```yaml
proxy:
  httpProxy: http://user:password@proxy.example.com:3128
  httpsProxy: http://user:password@proxy.example.com:3128
  noProxy: .{{ base_domain }},10.0.0.0/28,10.128.0.0/14,172.30.0.0/16,localhost,127.0.0.1,.cluster.local,.svc
```

### Additional Trust Bundle (MITM Proxy)

If your environment uses a TLS-intercepting proxy, add the trust bundle:

```yaml
additionalTrustBundlePolicy: Always
additionalTrustBundle: |
  -----BEGIN CERTIFICATE-----
  MIIDzTCCArWgAwIBAgIUXXXXXXXXXXXXXXXXXXXXXXXXXXXwDQYJKoZIhvcNAQEL
  ...
  -----END CERTIFICATE-----
```

### Disconnected or Pull-Through Proxy Environments

If your environment uses a mirror registry, pull-through cache, or artifact proxy (such as JFrog Artifactory or Sonatype Nexus), see [Configuring OpenShift for a Disconnected Registry](disconnected/openshift-config.md) for the full `imageDigestSources` configuration and setup instructions.

### Compact 3-Node Cluster (No Workers)

For a compact cluster where control plane nodes are schedulable and also run workloads, set `compute[0].replicas` to `0`. The three control plane nodes will handle both control plane and worker duties.

Do **not** add worker hosts to `agent-config.yaml`. List only the three control plane nodes with `role: master`.

## agent-config.yaml

The `agent-config.yaml` defines host-level configurations. Below is an example with two ethernet connections bonded together in an LACP bond with a VLAN.

!!! note "rootDeviceHints and interface names"
    If you do not know what the `rootDeviceHint` or your NIC's interface names are, do not guess. They will follow RHEL naming standards. Boot an example machine with a RHEL ISO and it will tell you how they show up. [Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html-single/installing_an_on-premise_cluster_with_the_agent-based_installer/index#root-device-hints_preparing-to-install-with-agent-based-installer)

```yaml
apiVersion: v1beta1
kind: AgentConfig
metadata:
  name: poc
rendezvousIP: 10.0.0.7        # This should be an IP of one of your nodes, preferably the first master node below. 
additionalNtpSources:
  - {{ ntp_server_1 }}
  - {{ ntp_server_2 }}
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
              - ip: 10.0.0.7
                prefix-length: 28
            dhcp: false
          ipv6:
            enabled: false
      dns-resolver:
        config:
          server:
            - {{ nameserver_ip }}
      routes:
        config:
          - destination: 0.0.0.0/0
            next-hop-address: 10.0.0.1
            next-hop-interface: bond0.3
            table-id: 254
```

Repeat the host entry for each control plane and worker node, updating hostname, MAC addresses, IP addresses, and role (`master` or `worker`). For a compact 3-node cluster, omit worker hosts entirely.

!!! note "NTP"
    Use the customer's NTP servers. `pool.ntp.org` only works if nodes have outbound internet, which most on-prem POCs do not. 

!!! note
    Notice the inconsistent labels and spellings in the OpenShift configs: 
    - `macAddress` in the interfaces stanza, but `mac-address` in the networkConfig stanza. 
    - `additionalNtpSources` is used in agent-config, but `additionalNTPServers` in install-config.

### Active-Backup Bond (No VLAN)

If your environment uses active-backup bonding instead of LACP:

```yaml
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
          ipv4:
            enabled: true
            address:
              - ip: 10.0.0.7
                prefix-length: 28
            dhcp: falsehttps://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html-single/installing_an_on-premise_cluster_with_the_agent-based_installer/index#root-device-hints_preparing-to-install-with-agent-based-installer
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

### Single NIC (No Bond)

For hosts with a single network interface:

```yaml
    networkConfig:
      interfaces:
        - name: eno1
          type: ethernet
          state: up
          mac-address: A1:B2:3C:4D:1E:11
          ipv4:
            enabled: true
            address:
              - ip: 10.0.0.7
                prefix-length: 28
            dhcp: false
          ipv6:
            enabled: false
      dns-resolver:
        config:
          server:
            - {{ nameserver_ip }}
      routes:
        config:
          - destination: 0.0.0.0/0
            next-hop-address: 10.0.0.1
            next-hop-interface: eno1
            table-id: 254
```

## Extra Manifests

If you have additional manifests to apply at install time (for example MachineConfigs or a `ClusterImagePolicy`), place them in an `openshift/` folder at the same level as `install-config.yaml` and `agent-config.yaml`. The agent installer embeds files from `openshift/` into the ISO.

```bash
mkdir -p openshift
```

!!! note
    Do not use a `cluster-manifests/` directory for this. That name is installer **output** from `openshift-install agent create cluster-manifests` (ZTP), not a user drop-in folder.

## Generate the ISO

Create a script `create-iso.sh` in your working directory:

!!! warning
    `openshift-install` consumes and deletes `install-config.yaml` and `agent-config.yaml` during image creation. The script below copies them into a subdirectory first so your originals are preserved.

```bash
#!/bin/bash
rm -rf install
mkdir install
cp install-config.yaml agent-config.yaml install
[ -d openshift ] && cp -r openshift install
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
  registry.redhat.io/rhel9/httpd-24:latest
```

Verify the ISO is accessible:

```bash
wget http://{{ installation_host }}:8080/agent.x86_64.iso
```

## Boot

Mount the ISO on each node via BMC virtual media (Redfish, iLO, iDRAC) and boot. 

!!! warning
    If you decide to use the BMC web UI to attach a virtual drive using the iso, make a separate copy of the ISO file (ocp-1, ocp-2, ocp-3, etc) for each of the hosts. If more than one host starts booting against the same file, the BMCs will sometimes have issues. 


## Monitor the Install 

When all hosts are booted, monitor the install:

```bash
openshift-install agent wait-for bootstrap-complete --dir=install
openshift-install agent wait-for install-complete --dir=install
```

At the end of the process, you will be presented with the URL for the cluster endpoint along with the kubeadmin credentials. They are also available in the `install` folder as `auth/kubeadmin-password` and `auth/kubeconfig`.

## Validate the Install

```bash
oc login --server=https://api.{{ cluster_name }}.{{ base_domain }}:6443 -u kubeadmin -p {{ password }}
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

## Documentation

- [Agent-Based Installer](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html-single/installing_an_on-premise_cluster_with_the_agent-based_installer/index)
