# Networking

OpenShift requires specific network configurations and firewall rules between nodes and external services.

## Network Requirements

| Network         | Purpose                          | CIDR Example     |
| --------------- | -------------------------------- | ---------------- |
| Machine Network | Node-to-node communication       | 10.0.0.0/24      |
| Cluster Network | Pod-to-pod communication (SDN)   | 10.128.0.0/14    |
| Service Network | Kubernetes service IPs           | 172.30.0.0/16    |

## Required Firewall Ports

| Port        | Protocol | Source           | Destination    | Purpose                    |
| ----------- | -------- | ---------------- | -------------- | -------------------------- |
| 6443        | TCP      | All              | Control Plane  | Kubernetes API             |
| 22623       | TCP      | Nodes            | Control Plane  | Machine Config Server      |
| 2379-2380   | TCP      | Control Plane    | Control Plane  | etcd                       |
| 10250       | TCP      | All nodes        | All nodes      | Kubelet                    |
| 4789        | UDP      | All nodes        | All nodes      | VXLAN (OVN-Kubernetes)     |
| 6081        | UDP      | All nodes        | All nodes      | Geneve (OVN-Kubernetes)    |
| 9000-9999   | TCP      | All nodes        | All nodes      | Node services              |
| 500         | UDP      | All nodes        | All nodes      | IPsec IKE                  |
| 4500        | UDP      | All nodes        | All nodes      | IPsec NAT-T               |
| 30000-32767 | TCP/UDP  | All nodes        | All nodes      | NodePort services          |

```bash
# Verify connectivity from installer to API endpoint
curl -k https://<control-plane-ip>:6443/healthz

# Verify machine config server
curl -k https://<control-plane-ip>:22623/healthz
```

---

## Details

### Machine Network

All cluster nodes must reside on the same Layer 2 network or have Layer 3 routing between them. DHCP is required for IPI installations; static IPs can be used with UPI or agent-based installs.

### NTP

All nodes must have synchronized time. Configure chrony to use a reliable NTP source:

```bash
sudo dnf install -y chrony
sudo systemctl enable --now chronyd
chronyc tracking
```

### Proxy Configuration

If your environment requires an HTTP proxy for outbound traffic, configure the proxy settings in the `install-config.yaml`:

```yaml
proxy:
  httpProxy: http://proxy.example.com:3128
  httpsProxy: http://proxy.example.com:3128
  noProxy: .cluster.local,.svc,10.0.0.0/24,172.30.0.0/16,10.128.0.0/14
```
