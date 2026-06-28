# Adding a Worker Node

[Official Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/nodes/adding-node-image)

## Create the YAML Configuration File

1. Create a file named `nodes-config.yaml`. This is similar to the `agent-config.yaml` used during installation.

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

2. Generate the node image ISO:

  ```bash
  oc adm node-image create nodes-config.yaml --dir=add --registry-config=~/pull-secret.txt
  ```

## Boot and Monitor

3. Boot the node with the generated ISO image (via BMC virtual media or physical media)
4. Monitor the progress:

  ```bash
  oc adm node-image monitor --ip-addresses {{ ip_addresses }}
  ```

## Approve Pending CSRs

5. Once the node appears, approve the pending certificate signing requests:

  ```bash
  oc get csr
  oc get csr | awk '{print $1}' | grep -v NAME | xargs oc adm certificate approve
  ```

6. Verify the node has joined the cluster:

  ```bash
  oc get nodes
  ```
