# Adding a Worker Node

## Create the YAML Configuration File

Create a file named `nodes-config.yaml`. This is similar to the `agent-config.yaml` used during installation.

### Simple Example (Single NIC)

```yaml
hosts:
  - hostname: extra-worker-1
    rootDeviceHints:
      deviceName: /dev/sda
    interfaces:
      - macAddress: 00:00:00:00:00:00
        name: eth0
    networkConfig:
      interfaces:
        - name: eth0
          type: ethernet
          state: up
          mac-address: 00:00:00:00:00:00
          ipv4:
            enabled: true
            address:
              - ip: 192.168.122.2
                prefix-length: 23
            dhcp: false
```

### Bonded Example

```yaml
hosts:
  - hostname: extra-worker-1
    rootDeviceHints:
      deviceName: /dev/sda
    interfaces:
      - macAddress: A0:B1:C2:D3:E4:F1
        name: eno1
      - macAddress: A0:B1:C2:D3:E4:F2
        name: eno2
    networkConfig:
      interfaces:
        - name: eno1
          type: ethernet
          state: up
          mac-address: A0:B1:C2:D3:E4:F1
          ipv4:
            enabled: false
          ipv6:
            enabled: false
        - name: eno2
          type: ethernet
          state: up
          mac-address: A0:B1:C2:D3:E4:F2
          ipv4:
            enabled: false
          ipv6:
            enabled: false
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
            enabled: true
            address:
              - ip: 10.0.0.10
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
            next-hop-interface: bond0
            table-id: 254
```

## Create the ISO Image

```bash
oc adm node-image create nodes-config.yaml --dir=add --registry-config=/path/to/pull-secret.txt
```

Boot the node with the generated ISO image.

## Monitor the Progress

```bash
oc adm node-image monitor --ip-addresses <ip_addresses>
```

## Approve Pending CSRs

```bash
oc get csr
oc get csr | awk '{print $1}' | grep -v NAME | xargs oc adm certificate approve
```
