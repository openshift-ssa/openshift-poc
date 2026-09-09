# Day-2 Operations

Operational procedures for managing the cluster after installation and configuration. These demonstrate that the customer team can independently perform common lifecycle tasks — a key POC success criterion.

| Procedure | What It Demonstrates | Typical Time |
|-----------|---------------------|--------------|
| [Cluster Upgrade](./cluster-upgrade.md) | Apply a z-stream or minor version update (minimal disruption with PDBs / LiveMigrate) | 45–90 min |
| [Add Worker Node](./add-worker-node.md) | Expand cluster capacity by adding a new worker node via ISO | 20–30 min |
| [Rotate SSH Keys](./rotate-ssh-keys.md) | Replace SSH keys on cluster nodes using MachineConfig | 10–15 min per pool |
| [Machine Config](./machine-config.md) | Create and apply node-level configuration with MachineConfig and Butane | 10–15 min per pool |
| [must-gather](./must-gather.md) | Collect cluster diagnostics for troubleshooting and support cases | 5–15 min |
| [Debugging MTU Mismatches](./debug-mtu.md) | Diagnose and fix MTU-related connectivity issues | Varies |

!!! tip "Recommended for Every POC"
    At minimum, demonstrate **Cluster Upgrade** and **must-gather** — these are the two day-2 tasks most commonly asked about by operations teams evaluating OpenShift.
