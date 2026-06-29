# Fleet Management

For fleet management, we recommend starting with a Single Node OpenShift (SNO) installation as the hub cluster, then installing Red Hat Advanced Cluster Management (ACM) to manage your cluster fleet at scale.

## Process Overview

1. Complete all [prerequisites](../prerequisites/index.md)
2. Set up the [installation host](../prerequisites/installation-host.md)
3. Install the [SNO hub cluster](sno-hub.md)
4. Install [storage on the hub](hub-storage.md)
5. Install [Advanced Cluster Management](acm-install.md)
6. Use ACM to [provision bare metal spoke clusters](acm-provision-bare-metal-cluster.md)

## Why Fleet Management?

| Benefit               | Description                                                         |
| --------------------- | ------------------------------------------------------------------- |
| Centralized control   | Manage all clusters from a single pane of glass                     |
| Consistent policy     | Enforce governance and security policies across the fleet           |
| Scalable provisioning | Create new clusters on demand through ACM                           |
| Lifecycle management  | Upgrade and maintain clusters centrally                             |
| Observability         | Unified view of cluster health and compliance                       |
