# Required Configuration

These must be completed before deploying any workloads.

1. **[NMState Operator](./nmstate.md)** — Required for advanced networking (bonds, VLANs, OVS bridges)
2. **[Storage](./storage/index.md)** — Install your CSI driver and create StorageClasses
3. **[Registry](./registry.md)** — Configure persistent storage for the internal image registry

You can run workloads with `kubeadmin` at this point. Configure an [identity provider](../optional/configuring-identity-providers.md) before demo day, and keep `kubeadmin` until at least one IdP user has `cluster-admin`.
