# VM Failover Test

This guide walks through testing VM failover by creating a RHEL 9 virtual machine, simulating a node failure, and verifying the VM restarts on a healthy node within the 120-second target. This assumes [Workload Availability](../../configure-the-cluster/workload-availability.md) is fully configured with the 120-second failover settings.

## Prerequisites

- OpenShift Virtualization installed and configured
- Workload Availability operators installed (NHC, SNR, Descheduler)
- RWX-capable StorageClass available (required for VM failover)
- At least 3 worker nodes

## Create the Virtual Machine

1. Create a namespace for the test:

  ```bash
  oc new-project vm-failover-test
  ```

2. Go to Virtualization -> VirtualMachines -> ensure you are in the `vm-failover-test` project -> click "Create VirtualMachine"
3. Select "From template" and choose "Red Hat Enterprise Linux 9"
4. Give it a name (e.g., `failover-test-vm`)
5. Ensure the VM is configured with:
    - `runStrategy: Always` (required — tells the cluster to restart the VM after node loss)
6. Click "Customize VirtualMachine" to edit the details before creating

!!! note "Failover vs live migration"
    This test simulates hard node failure (`systemctl reboot`). Recovery is a **cold restart** driven by Workload Availability (NHC/SNR) and `runStrategy: Always`. `evictionStrategy: LiveMigrate` applies to drains and upgrades — it does **not** live-migrate a VM off a node that has already died. You may still set LiveMigrate for day-2 drain behavior, but it is not what makes this failover test succeed.

### Add a Data Disk

7. Click on the "Disks" tab
8. Click "Add disk"
9. Configure the data disk:
    - Name: `data-disk`
    - Source: Blank
    - Size: 10 GiB
    - Type: Disk
    - StorageClass: your RWX-capable StorageClass
    - Access Mode: ReadWriteMany (RWX)

!!! warning
    Both the root disk and the data disk must use RWX access mode for failover to work. If either disk is RWO, the VM cannot start on a new node until the old node's lease expires (6+ minutes).

10. Click Add
11. Also verify the root disk is using RWX access mode — edit it if necessary

### Set Login Credentials

12. Open the **Scripts** tab
13. Under **Cloud-init**, set a guest password (RHEL cloud images have no usable default):

  ```yaml
  #cloud-config
  user: cloud-user
  password: Pass123!
  chpasswd:
    expire: false
  ```

### Start the VM

14. Click "Create VirtualMachine"
15. Wait for the VM status to show "Running"

## Verify the VM is Running

16. From the CLI, confirm the VM is running and note which node it is on:

  ```bash
  oc get vmi failover-test-vm -n vm-failover-test -o wide
  ```

  The `NODE` column shows where the VM is currently scheduled.

17. Check the IP address assigned to the VM:

  ```bash
  oc get vmi failover-test-vm -n vm-failover-test -o jsonpath='{.status.interfaces}' | jq
  ```

  Record the IP address — you will verify it stays the same after failover.

  !!! note "Persistent IP Across Failover"
      If you have configured a ClusterUserDefinedNetwork (CUDN) with persistent IPAM and attached the VM to it, the IP address is allocated to the VM itself (not the node) and will follow the VM to the new node. Without a CUDN, the VM gets a new pod network IP after failover — the VM still recovers, but clients connecting by IP will need to discover the new address.

18. Optionally, open the VM console from the WebUI to confirm the guest OS is up:
    - Virtualization -> VirtualMachines -> click `failover-test-vm` -> Console tab
    - Log in as `cloud-user` / `Pass123!`

## Simulate Node Failure

19. Record the node name where the VM is running:

  ```bash
  NODE=$(oc get vmi failover-test-vm -n vm-failover-test -o jsonpath='{.status.nodeName}')
  echo "VM is on node: $NODE"
  ```

20. Start a timer and then restart the node to simulate a failure:

  ```bash
  date +%T && oc debug node/$NODE -- chroot /host systemctl reboot
  ```

!!! note
    This simulates an unexpected node reboot. In a real failure scenario (power loss, kernel panic), the node would simply stop responding without a graceful shutdown.

## Watch the Failover

21. Immediately watch the VM instance for changes:

  ```bash
  oc get vmi failover-test-vm -n vm-failover-test -w
  ```

  You should see the following sequence:
    - VM status remains `Running` initially (node hasn't been marked unhealthy yet)
    - After ~50s: node is marked `NotReady`
    - After ~80s: NHC creates a `SelfNodeRemediation` CR
    - After ~85-90s: node gets the `out-of-service` taint, pods are deleted
    - After ~100-120s: VM restarts on a different node

22. Once the VM shows `Running` again, check the timestamp:

  ```bash
  date +%T
  oc get vmi failover-test-vm -n vm-failover-test -o wide
  ```

  The `NODE` column should show a different node than before.

## Verify the Failover

23. Confirm the VM is fully running on the new node:

  ```bash
  oc get vmi failover-test-vm -n vm-failover-test -o jsonpath='{.status.phase}'
  ```

  Should output: `Running`

24. Verify the IP address followed the VM to the new node:

  ```bash
  oc get vmi failover-test-vm -n vm-failover-test -o jsonpath='{.status.interfaces}' | jq
  ```

  If you have a CUDN with persistent IPAM configured, the IP address should be **identical** to what was recorded before the failover — the IP is allocated to the VM, not the node. Without a CUDN, the VM receives a new pod network IP, which is expected.

25. Check the data disk is still attached:

  ```bash
  oc get vmi failover-test-vm -n vm-failover-test -o jsonpath='{.spec.volumes[*].name}'
  ```

26. Open the VM console from the WebUI to confirm the guest OS has booted:
    - Virtualization -> VirtualMachines -> click `failover-test-vm` -> Console tab
    - Login and verify the data disk is mounted (if it was mounted in the guest)
    - Run `ip addr` inside the guest to confirm the IP matches

27. Review the remediation events:

  ```bash
  oc get selfnoderemediation -A
  oc get events -n openshift-workload-availability --sort-by='.lastTimestamp'
  ```

## Expected Timeline

| Time    | Event                                                |
| ------- | ---------------------------------------------------- |
| T+0s    | Node reboots — stops responding                      |
| T+~50s  | API server marks node `Ready=Unknown`                |
| T+~80s  | NHC threshold (30s) breached, remediation CR created |
| T+~85s  | SNR applies `out-of-service` taint                   |
| T+~90s  | Pods force-deleted, volumes detached                 |
| T+~100s | New VMI scheduled on healthy node, storage attached  |
| T+~120s | VM fully running on new node                         |

## Cleanup

28. Delete the test VM:

  ```bash
  oc delete vm failover-test-vm -n vm-failover-test
  ```

29. Wait for the rebooted node to come back and verify it rejoins the cluster:

  ```bash
  oc get nodes -w
  ```

  The node should return to `Ready` status after it finishes rebooting.

30. Delete the test namespace:

  ```bash
  oc delete project vm-failover-test
  ```

!!! tip
    If the failover took significantly longer than 120 seconds, check:

    - Storage access mode (must be RWX)
    - NHC `unhealthyConditions.duration` is set to `30s`
    - Self Node Remediation pods are running on all nodes: `oc get pods -n openshift-workload-availability`
    - Hardware watchdog is available: `oc debug node/<node> -- chroot /host ls /dev/watchdog*`
