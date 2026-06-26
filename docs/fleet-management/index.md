# Fleet Management

For fleet management, we recommend starting with a Single Node OpenShift (SNO) installation using the [Assisted Installer](https://console.redhat.com/openshift/assisted-installer/clusters). Once completed, install and configure [Red Hat Advanced Cluster Management for Kubernetes](https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/latest) (ACM) to use it as your cluster management hub.

## Process Overview

1. Complete all [prerequisites](../prerequisites/index.md)
2. Install a Single Node OpenShift cluster via the [Assisted Installer](../standalone/assisted-installer.md)
3. Install Red Hat Advanced Cluster Management on the hub cluster
4. Use ACM to provision and manage additional spoke clusters

## Architecture

```
┌─────────────────────────────────────────┐
│           Hub Cluster (SNO)             │
│                                         │
│  ┌─────────┐  ┌─────────┐  ┌────────┐  │
│  │   ACM   │  │  GitOps │  │  ACS   │  │
│  └─────────┘  └─────────┘  └────────┘  │
│                                         │
└────────────────┬────────────────────────┘
                 │
      ┌──────────┼──────────┐
      │          │          │
      ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│  Spoke 1 │ │  Spoke 2 │ │  Spoke N │
│ (Dev)    │ │ (Test)   │ │ (Prod)   │
└──────────┘ └──────────┘ └──────────┘
```

## Why Fleet Management?

| Benefit              | Description                                                         |
| -------------------- | ------------------------------------------------------------------- |
| Centralized control  | Manage all clusters from a single pane of glass                     |
| Consistent policy    | Enforce governance and security policies across the fleet           |
| Scalable provisioning | Create new clusters on demand through ACM                          |
| Lifecycle management | Upgrade and maintain clusters centrally                             |
| Observability        | Unified view of cluster health and compliance                       |
