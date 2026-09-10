# Redfish Network Discovery for NMStateConfig

When provisioning spoke clusters with [Hub and Spoke](./hub-and-spoke.md), you need `NMStateConfig` resources with each host's MAC address and interface name. Instead of manually collecting this from each server, you can query the BMC via the Redfish API to discover network interfaces and generate the YAML automatically.

## How It Works

1. Query the BMC's Redfish endpoint to list all ethernet interfaces
2. Extract MAC addresses, interface IDs, link status, and speed
3. Generate `NMStateConfig` YAML with the correct MAC-to-interface mapping

!!! note
    Redfish interface IDs (e.g. Dell's `NIC.Integrated.1-1-1`) may not match the Linux interface name (e.g. `eno1`). This is fine — the `interfaces[].macAddress` field in the NMStateConfig maps the config to the correct physical NIC at boot time, regardless of what Linux names it.

## Prerequisites

- BMC network access from your workstation or installation host
- BMC credentials (same ones used for BareMetalHost resources)
- `curl` and `jq` installed

## Exploring Interfaces Manually

Before automating, it's useful to explore what a server exposes:

```bash
# Discover the system ID
curl -sk https://{{ bmc_ip }}/redfish/v1/Systems/ \
  -u {{ bmc_user }}:{{ bmc_pass }} | jq '.Members'
```

```bash
# List all ethernet interfaces
curl -sk https://{{ bmc_ip }}/redfish/v1/Systems/{{ system_id }}/EthernetInterfaces/ \
  -u {{ bmc_user }}:{{ bmc_pass }} | jq '.Members'
```

```bash
# Get details for a specific interface
curl -sk https://{{ bmc_ip }}/redfish/v1/Systems/{{ system_id }}/EthernetInterfaces/{{ nic_id }} \
  -u {{ bmc_user }}:{{ bmc_pass }} | jq '{Id, MACAddress, SpeedMbps, LinkStatus, Status}'
```

??? example "Example output — Dell iDRAC"
    ```json
    {
      "Id": "NIC.Integrated.1-1-1",
      "MACAddress": "B0:26:28:E3:A4:10",
      "SpeedMbps": 25000,
      "LinkStatus": "LinkUp",
      "Status": {
        "Health": "OK",
        "State": "Enabled"
      }
    }
    ```

??? example "Example output — HPE iLO"
    ```json
    {
      "Id": "1",
      "MACAddress": "98:F2:B3:22:6C:40",
      "SpeedMbps": 10000,
      "LinkStatus": "LinkUp",
      "Status": {
        "Health": "OK",
        "State": "Enabled"
      }
    }
    ```

## Generate Script

Save this as `generate-nmstate.sh`:

```bash
#!/bin/bash
# generate-nmstate.sh — Query BMC via Redfish and generate NMStateConfig YAML
#
# Usage:
#   ./generate-nmstate.sh <bmc_ip> <bmc_user> <bmc_pass> <spoke_cluster> \
#     <hostname> <host_ip> <prefix> <gateway> <dns_server> [interface_filter]
#
# Arguments:
#   bmc_ip            BMC IP address or hostname
#   bmc_user          BMC username
#   bmc_pass          BMC password
#   spoke_cluster     Spoke cluster namespace name
#   hostname          Host/node name for the NMStateConfig
#   host_ip           Static IP to assign to this host
#   prefix            Subnet prefix length (e.g. 24)
#   gateway           Default gateway IP
#   dns_server        DNS server IP
#   interface_filter  Optional regex to select a NIC (e.g. "Integrated" or "eno1")
#                     Defaults to "." (match all — picks first alphabetically)

set -euo pipefail

BMC_IP="$1"
BMC_USER="$2"
BMC_PASS="$3"
SPOKE_CLUSTER="$4"
HOSTNAME="$5"
HOST_IP="$6"
PREFIX="$7"
GATEWAY="$8"
DNS="$9"
FILTER="${10:-.}"

# Discover the system ID
SYSTEM_ID=$(curl -sk "https://${BMC_IP}/redfish/v1/Systems/" \
  -u "${BMC_USER}:${BMC_PASS}" | jq -r '.Members[0]."@odata.id"' | sed 's|.*/||')

echo "# System: ${SYSTEM_ID}" >&2

# Get all ethernet interface URIs
INTERFACES=$(curl -sk "https://${BMC_IP}/redfish/v1/Systems/${SYSTEM_ID}/EthernetInterfaces" \
  -u "${BMC_USER}:${BMC_PASS}" | jq -r '.Members[]."@odata.id"')

echo "# Discovered interfaces:" >&2

declare -A MACS

for iface_path in $INTERFACES; do
  iface_data=$(curl -sk "https://${BMC_IP}${iface_path}" -u "${BMC_USER}:${BMC_PASS}")

  iface_id=$(echo "$iface_data" | jq -r '.Id')
  mac=$(echo "$iface_data" | jq -r '.MACAddress // .PermanentMACAddress // "unknown"')
  speed=$(echo "$iface_data" | jq -r '.SpeedMbps // "N/A"')
  status=$(echo "$iface_data" | jq -r '.Status.State // "unknown"')
  link=$(echo "$iface_data" | jq -r '.LinkStatus // "unknown"')

  echo "#   ${iface_id}: MAC=${mac}  Speed=${speed}Mbps  State=${status}  Link=${link}" >&2

  if echo "$iface_id" | grep -qE "$FILTER"; then
    MACS["$iface_id"]="$mac"
  fi
done

# Pick the first matching interface (sorted alphabetically)
SELECTED_ID=$(echo "${!MACS[@]}" | tr ' ' '\n' | sort | head -1)
SELECTED_MAC="${MACS[$SELECTED_ID]}"

if [ -z "$SELECTED_MAC" ] || [ "$SELECTED_MAC" = "unknown" ]; then
  echo "ERROR: No interface matched filter '${FILTER}'" >&2
  exit 1
fi

echo "#" >&2
echo "# Selected: ${SELECTED_ID} (${SELECTED_MAC})" >&2

# Generate NMStateConfig YAML
cat <<EOF
apiVersion: agent-install.openshift.io/v1beta1
kind: NMStateConfig
metadata:
  name: ${HOSTNAME}
  namespace: ${SPOKE_CLUSTER}
  labels:
    infraenvs.agent-install.openshift.io: ${SPOKE_CLUSTER}
spec:
  config:
    interfaces:
      - name: ${SELECTED_ID}
        type: ethernet
        state: up
        ipv4:
          enabled: true
          address:
            - ip: ${HOST_IP}
              prefix-length: ${PREFIX}
          dhcp: false
    dns-resolver:
      config:
        server:
          - ${DNS}
    routes:
      config:
        - destination: 0.0.0.0/0
          next-hop-address: ${GATEWAY}
          next-hop-interface: ${SELECTED_ID}
  interfaces:
    - name: ${SELECTED_ID}
      macAddress: "${SELECTED_MAC}"
EOF
```

```bash
chmod +x generate-nmstate.sh
```

## Usage

### Single Host

```bash
./generate-nmstate.sh 10.0.0.101 admin 'P@ssw0rd' spoke1 \
  worker-0 192.168.1.50 24 192.168.1.1 10.0.0.10 > worker-0-nmstate.yaml
```

Stderr shows all discovered interfaces so you can verify the right one was selected:

```
# System: System.Embedded.1
# Discovered interfaces:
#   NIC.Integrated.1-1-1: MAC=B0:26:28:E3:A4:10  Speed=25000Mbps  State=Enabled  Link=LinkUp
#   NIC.Integrated.1-2-1: MAC=B0:26:28:E3:A4:11  Speed=25000Mbps  State=Enabled  Link=LinkDown
#   NIC.Slot.3-1-1: MAC=04:7B:CB:3E:72:80  Speed=25000Mbps  State=Enabled  Link=LinkUp
#
# Selected: NIC.Integrated.1-1-1 (B0:26:28:E3:A4:10)
```

### Filter to a Specific NIC

Use the optional filter argument to target a specific interface pattern:

```bash
# Only match integrated NICs (Dell)
./generate-nmstate.sh 10.0.0.101 admin 'P@ssw0rd' spoke1 \
  worker-0 192.168.1.50 24 192.168.1.1 10.0.0.10 "Integrated" > worker-0-nmstate.yaml

# Only match slot 3 NICs
./generate-nmstate.sh 10.0.0.101 admin 'P@ssw0rd' spoke1 \
  worker-0 192.168.1.50 24 192.168.1.1 10.0.0.10 "Slot.3" > worker-0-nmstate.yaml
```

### Batch from a CSV

Create a `hosts.csv` file:

```csv
10.0.0.101,admin,P@ssw0rd,ctrl-0,192.168.1.10
10.0.0.102,admin,P@ssw0rd,ctrl-1,192.168.1.11
10.0.0.103,admin,P@ssw0rd,ctrl-2,192.168.1.12
10.0.0.104,admin,P@ssw0rd,worker-0,192.168.1.20
10.0.0.105,admin,P@ssw0rd,worker-1,192.168.1.21
10.0.0.106,admin,P@ssw0rd,worker-2,192.168.1.22
```

Run the batch:

```bash
SPOKE=spoke1
PREFIX=24
GATEWAY=192.168.1.1
DNS=10.0.0.10

while IFS=, read -r bmc_ip bmc_user bmc_pass hostname host_ip; do
  ./generate-nmstate.sh "$bmc_ip" "$bmc_user" "$bmc_pass" \
    "$SPOKE" "$hostname" "$host_ip" "$PREFIX" "$GATEWAY" "$DNS" \
    > "${hostname}-nmstate.yaml"
  echo "Generated ${hostname}-nmstate.yaml"
done < hosts.csv
```

Review the generated files, then apply them all before creating BareMetalHosts:

```bash
oc apply -f ./*-nmstate.yaml
```

### Discovery-Only Mode

To just list interfaces without generating YAML, query each BMC directly:

```bash
while IFS=, read -r bmc_ip bmc_user bmc_pass hostname _; do
  echo "=== ${hostname} (${bmc_ip}) ==="
  SYSTEM_ID=$(curl -sk "https://${bmc_ip}/redfish/v1/Systems/" \
    -u "${bmc_user}:${bmc_pass}" | jq -r '.Members[0]."@odata.id"' | sed 's|.*/||')

  curl -sk "https://${bmc_ip}/redfish/v1/Systems/${SYSTEM_ID}/EthernetInterfaces" \
    -u "${bmc_user}:${bmc_pass}" | jq -r '.Members[]."@odata.id"' | while read uri; do
    curl -sk "https://${bmc_ip}${uri}" -u "${bmc_user}:${bmc_pass}" \
      | jq '{Id, MACAddress, SpeedMbps, LinkStatus}'
  done
  echo
done < hosts.csv
```

## Tips

!!! tip "Choosing the right NIC"
    Most servers have multiple interfaces — management, data, storage, and possibly BMC shared ports. Look for:

    - **LinkUp** status (connected to the machine network)
    - **Speed** matching your expected network (e.g. 25Gbps data vs 1Gbps management)
    - **Integrated** NICs for onboard ports vs **Slot** NICs for add-in cards

!!! tip "Bonded interfaces"
    If your spoke cluster uses bonded NICs, generate the NMStateConfig with both interfaces and add the bond configuration manually. The script gives you the MAC addresses — you supply the bond config:

    ```yaml
    spec:
      config:
        interfaces:
          - name: bond0
            type: bond
            state: up
            ipv4:
              enabled: true
              address:
                - ip: {{ host_ip }}
                  prefix-length: {{ prefix }}
              dhcp: false
            link-aggregation:
              mode: 802.3ad
              port:
                - eno1
                - eno2
          - name: eno1
            type: ethernet
            state: up
          - name: eno2
            type: ethernet
            state: up
      interfaces:
        - name: eno1
          macAddress: "B0:26:28:E3:A4:10"
        - name: eno2
          macAddress: "B0:26:28:E3:A4:11"
    ```

!!! warning "VLAN tagging"
    If your machine network uses a VLAN, add a VLAN interface on top of the physical NIC in the NMStateConfig. The script does not detect VLAN configuration — that depends on your switch config, not the BMC.
