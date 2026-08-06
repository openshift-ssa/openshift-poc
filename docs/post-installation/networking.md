# Networking

[OpenShift Networking Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/networking_operators/index)

This page provides examples for configuring advanced networking post-installation using the NMState Operator and OVN-Kubernetes. See [Prerequisites — Networking](../prerequisites/networking.md) for the network architecture and planning guidance these examples implement.

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

| Concept                             | Where      | Managed By |
| ----------------------------------- | ---------- | ---------- |
| Switch                              | Physical   | Switch     |
| Ethernet                            | Linux      | NNCP       |
| Bond                                | Linux      | NNCP       |
| OVS Bridge                          | Linux      | NNCP       |
| OVN Bridge Mapping                  | OVN-K      | NNCP       |
| Localnet                            | OVN-K      | NNCP       |
| Cluster User Defined Network (CUDN) | OVN-K      | —         |
| Network Attachment Definition       | OVN-K      | CUDN       |
| Virtual Ethernet Pair               | Kubernetes | CNI        |

### xmit_hash_policy explanations

The main xmit_hash_policy values for 802.3ad bonds:

- layer2 — Hashes on source/destination MAC only. All traffic between two given MACs takes a single slave, so a single node-to-node flow can't spread across members. Standard 802.3ad compliant.
- layer2+3 — Hashes on MAC plus IP addresses. Better distribution than layer2 across different IP pairs, still 802.3ad compliant. Good default when traffic spans multiple hosts/subnets but you don't want L4 hashing.
- layer3+4 — Hashes on IP addresses plus L4 (TCP/UDP) ports. Distributes individual connections between the same two hosts across different slaves, which is why it's good for NVMe/TCP and iSCSI with multiple sessions. Not strictly 802.3ad compliant because fragmented packets can reorder, but widely used.
- encap2+3 — Like layer2+3 but uses inner headers for encapsulated traffic (e.g. VXLAN/tunneled), falling back to outer headers if it can't parse the inner. Useful on overlay/tunnel-heavy paths.
- encap3+4 — Like layer3+4 but for encapsulated traffic, hashing on inner L3/L4 when available.
- vlan+srcmac — Hashes on VLAN ID and source MAC. Niche; mainly for setups where you want per-VLAN slave selection.

For storage over LACP, layer3+4 is the usual choice because it lets multiple sessions/connections between the same two endpoints actually use both bond members. Just make sure the switch's port-channel hash policy is set comparably (e.g. src-dst-port / L4 hashing) so distribution is balanced in both directions—the host and switch hash independently for their respective transmit directions.

## NodeNetworkConfigurationPolicy Examples

### Bonds and Vlans

#### 2-eth Bond1 (LACP) with IP

```yaml
apiVersion: nmstate.io/v1
kind: NodeNetworkConfigurationPolicy
metadata:
  name: bond1-{{ hostname }}
spec:
  nodeSelector:
    kubernetes.io/hostname: {{ hostname }}
  desiredState:
    interfaces:
      - name: bond1
        type: bond
        state: up
        # mtu: 9000
        # mtu: 1500
        link-aggregation:
          mode: 802.3ad
          port:
            - {{ interface_name1 }}
            - {{ interface_name2 }}
          options:
            miimon: "100"
            lacp_rate: fast
            xmit_hash_policy: layer3+4
        ipv4:
          enabled: true
          address:
            - ip: {{ ip_address }}
              prefix-length: 24
          dhcp: false
        ipv6:
          enabled: false
```

Creates an LACP bond with a static IP assigned directly on the bond interface. Because the bond itself carries the IP (no VLAN tagging), the switch ports must either be in access mode or have a native/untagged VLAN configured. The commented-out `mtu` lines show where to set jumbo frames if needed. `lacp_rate: fast` sends LACPDUs every second instead of the default 30 seconds, enabling faster link-failure detection.

#### 2-eth Bond1 (LACP) with trunk

```yaml
apiVersion: nmstate.io/v1
kind: NodeNetworkConfigurationPolicy
metadata:
  name: bond1-{{ hostname }}
spec:
  nodeSelector:
    kubernetes.io/hostname: {{ hostname }}
  desiredState:
    interfaces:
      - name: bond1
        type: bond
        state: up
        link-aggregation:
          mode: 802.3ad
          port:
            - {{ interface_name1 }}
            - {{ interface_name2 }}
          options:
            miimon: "100"
            lacp_rate: fast
            xmit_hash_policy: layer3+4
        ipv4:
          enabled: false
        ipv6:
          enabled: false
```

Creates an LACP bond configured as a trunk — no IP is assigned to the bond itself. Traffic flows through VLAN sub-interfaces defined in separate policies. The switch side must have the corresponding port-channel configured as a trunk passing the needed VLAN IDs. This is the typical building block when you need multiple VLANs over a single bonded uplink.

#### 2-eth Bond (LACP) with VLAN

```yaml
apiVersion: nmstate.io/v1
kind: NodeNetworkConfigurationPolicy
metadata:
  name: 2-eth-bond-lacp-vlan-{{ hostname }}
spec:
  nodeSelector:
    kubernetes.io/hostname: {{ hostname }}
  desiredState:
    interfaces:
      - name: bond1
        type: bond
        state: up
        link-aggregation:
          mode: 802.3ad
          port:
            - {{ interface_name1 }}
            - {{ interface_name2 }}
          options:
            miimon: "100"
            lacp_rate: fast
            xmit_hash_policy: layer3+4
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

Creates an LACP bond trunk and a VLAN sub-interface with a static IP in a single policy. The bond carries no IP; the VLAN interface (`bond1.{{ vlan_id }}`) is where the address lives. Defining both in the same NNCP ensures they are applied atomically — if either fails, NMState rolls back both. The switch must trunk the specified VLAN ID on the port-channel.

#### 2-eth Bond (Active-Backup) with VLAN

```yaml
apiVersion: nmstate.io/v1
kind: NodeNetworkConfigurationPolicy
metadata:
  name: 2-eth-bond-active-backup-vlan-{{ hostname }}
spec:
  nodeSelector:
    kubernetes.io/hostname: {{ hostname }}
  desiredState:
    interfaces:
      - name: bond1
        type: bond
        state: up
        link-aggregation:
          mode: active-backup
          port:
            - {{ interface_name1 }}
            - {{ interface_name2 }}
          options:
            miimon: "100"
            primary: {{ interface_name1 }}
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

Same pattern as the LACP-with-VLAN example above but using `active-backup` mode instead of `802.3ad`. No switch-side LACP or port-channel configuration is required — only one NIC is active at a time, so the switch sees a single MAC. The `primary` option designates the preferred active interface; the other takes over only on failure. There is no `xmit_hash_policy` because there is no load distribution across members. Simpler to set up but provides redundancy only, not bandwidth aggregation.

#### Storage Network Bond with Jumbo Frames (MTU 9000)

This configures a dedicated storage bond with MTU 9000 and a VLAN for storage traffic. Set MTU on the bond (ports inherit it) and explicitly on any VLAN interface on top.

```yaml
apiVersion: nmstate.io/v1
kind: NodeNetworkConfigurationPolicy
metadata:
  name: storage-bond-mtu9000-{{ hostname }}
spec:
  nodeSelector:
    kubernetes.io/hostname: {{ hostname }}
  desiredState:
    interfaces:
      - name: bond-storage
        type: bond
        state: up
        mtu: 9000
        link-aggregation:
          mode: 802.3ad
          port:
            - {{ interface_name1 }}
            - {{ interface_name2 }}
          options:
            miimon: "100"
            lacp_rate: fast
            xmit_hash_policy: layer3+4
        ipv4:
          enabled: false
        ipv6:
          enabled: false
      - name: bond-storage.{{ storage_vlan_id }}
        type: vlan
        state: up
        mtu: 9000
        vlan:
          base-iface: bond-storage
          id: {{ storage_vlan_id }}
        ipv4:
          enabled: true
          address:
            - ip: {{ storage_ip }}
              prefix-length: 24
          dhcp: false
        ipv6:
          enabled: false
```

Builds a dedicated storage bond with jumbo frames and a tagged VLAN for storage traffic. MTU 9000 is set on the bond (the kernel propagates it to the ethernet port members) and explicitly on the VLAN interface, since VLANs do not automatically inherit MTU changes from their parent. The physical switch ports and any intermediate infrastructure must also support the MTU end-to-end or frames will be silently dropped. `xmit_hash_policy: layer3+4` is set so that storage protocols using multiple TCP sessions (e.g. NVMe/TCP, iSCSI) distribute connections across bond members — make sure the switch port-channel hash policy matches (e.g. src-dst-port / L4 hashing).

!!! note
    Set MTU on the bond (ports inherit it) and explicitly on any VLAN interface on top. Verify after applying with:

    ``bash     oc debug node/{{ node_name }} -- chroot /host ip link show bond-storage     ``

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

Creates an OVS bridge on top of an existing bond and maps it to an OVN localnet. The bond must already be configured (via a separate NNCP) before this policy is applied. `allow-extra-patch-ports: true` is required for OVN-Kubernetes integration, and STP is disabled because the underlying bond already provides link redundancy. The `bridge-mappings` section ties the OVS bridge to a logical localnet name (`localnet-bridge-trunk`) — this is the name that ClusterUserDefinedNetworks reference via `physicalNetworkName` to attach pod traffic to the physical network.

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
        values: ["{{ namespace1 }}", "{{ namespace2 }}"]
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

Creates a cluster-scoped localnet network with OVN-managed IP address assignment. The `namespaceSelector` controls which namespaces can attach pods to this network — only pods in matching namespaces will get a secondary interface. `physicalNetworkName` must exactly match the localnet name from the OVS bridge NNCP above. The `excludeSubnets` entries reserve the gateway and broadcast addresses so OVN does not hand them out to pods. `lifecycle: Persistent` ensures pod IPs survive pod restarts, which is important for stateful workloads or when external systems maintain firewall rules based on pod addresses.

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
        values: ["{{ namespace1 }}", "{{ namespace2 }}"]
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

Same localnet topology as above but with IPAM disabled — OVN provides layer-2 connectivity only and does not assign IP addresses to pods. Use this when an external DHCP server on the VLAN handles addressing, or when the application manages its own IPs (e.g. VMs with static network configs via OpenShift Virtualization). No `subnets` or `excludeSubnets` are needed since OVN is not allocating addresses.
