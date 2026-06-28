# Networking

[OpenShift Networking Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/networking_operators/index)

This page provides examples for configuring advanced networking post-installation using the NMState Operator and OVN-Kubernetes.

## Overview

From a Linux configuration perspective:

- NICs can be bonded (`type: bond`)
- Bonds have a mode of `802.3ad` (LACP), `balance-xor`, or `active-backup`
- VLANs can have a `base-iface` of an existing `ethernet` or `bond`
- You can have multiple VLANs from a trunked `base-iface`

### Typical OpenShift Production Setup — 3 Bonds (LACP)

- `bond0` — management bond for cluster traffic
- `bond1` — data bond for pod network
- `bond2` — storage network

## The Full Stack for Underlay Networking

| Concept                              | Where      | Managed By |
| ------------------------------------ | ---------- | ---------- |
| Switch                               | Physical   | Switch     |
| Ethernet                             | Linux      | NNCP       |
| Bond                                 | Linux      | NNCP       |
| OVS Bridge                           | Linux      | NNCP       |
| OVN Bridge Mapping                   | OVN-K      | NNCP       |
| Localnet                             | OVN-K      | NNCP       |
| Cluster User Defined Network (CUDN)  | OVN-K      | —          |
| Network Attachment Definition        | OVN-K      | CUDN       |
| Virtual Ethernet Pair                | Kubernetes | CNI        |

## NodeNetworkConfigurationPolicy Examples

### 2-eth Bond (LACP) with VLAN

```yaml
apiVersion: nmstate.io/v1
kind: NodeNetworkConfigurationPolicy
metadata:
  name: 2-eth-bond-lacp-vlan
spec:
  nodeSelector:
    kubernetes.io/hostname: {{ hostname }}
  desiredState:
    interfaces:
      - name: {{ device_name }}
        type: ethernet
        state: up
        mac-address: {{ mac_address }}
        ipv4:
          enabled: false
        ipv6:
          enabled: false
      - name: <devicename2>
        type: ethernet
        state: up
        mac-address: <macaddress2>
        ipv4:
          enabled: false
        ipv6:
          enabled: false
      - name: bond1
        type: bond
        state: up
        link-aggregation:
          mode: 802.3ad
          port:
            - {{ device_name }}
            - <devicename2>
          options:
            miimon: "100"
            lacp_rate: fast
        ipv4:
          enabled: false
        ipv6:
          enabled: false
      - name: bond1.{{ vlan_id }}
        type: vlan
        state: up
        vlan:
          base-iface: bond1
          id: {{ vlan_id }}
        ipv4:
          enabled: true
          address:
            - ip: {{ ip_address }}
              prefix-length: 28
          dhcp: false
        ipv6:
          enabled: false
```

### 2-eth Bond (Active-Backup) with VLAN

```yaml
apiVersion: nmstate.io/v1
kind: NodeNetworkConfigurationPolicy
metadata:
  name: 2-eth-bond-active-backup-vlan
spec:
  nodeSelector:
    kubernetes.io/hostname: {{ hostname }}
  desiredState:
    interfaces:
      - name: {{ device_name }}
        type: ethernet
        state: up
        mac-address: {{ mac_address }}
        ipv4:
          enabled: false
        ipv6:
          enabled: false
      - name: <devicename2>
        type: ethernet
        state: up
        mac-address: <macaddress2>
        ipv4:
          enabled: false
        ipv6:
          enabled: false
      - name: bond1
        type: bond
        state: up
        link-aggregation:
          mode: active-backup
          port:
            - {{ device_name }}
            - <devicename2>
          options:
            miimon: "100"
            primary: {{ device_name }}
        ipv4:
          enabled: false
        ipv6:
          enabled: false
      - name: bond1.{{ vlan_id }}
        type: vlan
        state: up
        vlan:
          base-iface: bond1
          id: {{ vlan_id }}
        ipv4:
          enabled: true
          address:
            - ip: {{ ip_address }}
              prefix-length: 28
          dhcp: false
        ipv6:
          enabled: false
```

### OVS Bridge Trunk

This assumes an existing `bond1` on worker nodes:

```yaml
apiVersion: nmstate.io/v1
kind: NodeNetworkConfigurationPolicy
metadata:
  name: ovs-bridge-trunk-nncp
spec:
  nodeSelector:
    node-role.kubernetes.io/worker: ""
  desiredState:
    interfaces:
      - name: ovs-bridge-trunk
        type: ovs-bridge
        state: up
        bridge:
          port:
            - name: bond1
          allow-extra-patch-ports: true
          options:
            stp: false
    ovn:
      bridge-mappings:
        - localnet: localnet-bridge-trunk
          bridge: ovs-bridge-trunk
          state: present
```

## ClusterUserDefinedNetwork

### CUDN with IPAM

```yaml
apiVersion: k8s.ovn.org/v1
kind: ClusterUserDefinedNetwork
metadata:
  name: cudn-with-ipam
spec:
  namespaceSelector:
    matchExpressions:
      - key: kubernetes.io/metadata.name
        operator: In
        values: ["{{ namespace }}", "{{ namespace2 }}"]
  network:
    topology: Localnet
    localnet:
      role: Secondary
      physicalNetworkName: localnet-bridge-trunk
      vlan:
        mode: Access
        access:
          id: 4
      subnets:
        - "10.4.0.0/24"
      excludeSubnets:
        - "10.4.0.0/31"
        - "10.4.0.255/32"
      ipam:
        mode: Enabled
        lifecycle: Persistent
```

### CUDN without IPAM

```yaml
apiVersion: k8s.ovn.org/v1
kind: ClusterUserDefinedNetwork
metadata:
  name: cudn-no-ipam
spec:
  namespaceSelector:
    matchExpressions:
      - key: kubernetes.io/metadata.name
        operator: In
        values: ["{{ namespace }}", "{{ namespace2 }}"]
  network:
    topology: Localnet
    localnet:
      role: Secondary
      physicalNetworkName: localnet-bridge-trunk
      vlan:
        mode: Access
        access:
          id: 4
      ipam:
        mode: Disabled
```
