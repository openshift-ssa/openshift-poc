# VM Failover Test

This guide walks through testing VM failover by creating a RHEL 9 virtual machine, simulating a node failure, and verifying the VM restarts on a healthy node within the 120-second target. This assumes [Workload Availability](../post-installation/workload-availability.md) is fully configured with the 120-second failover settings.

## Prerequisites

- OpenShift Virtualization installed and configured
- Workload Availability operators installed (NHC, SNR, Descheduler)
- RWX-capable StorageClass available (required for VM failover)
- At least 3 worker nodes

## Create the Virtual Machine

1. Go to Virtualization -> VirtualMachines -> click "Create VirtualMachine"
2. Select "From template" and choose "Red Hat Enterprise Linux 9"
3. Give it a name (e.g., `failover-test-vm`)
4. Ensure the VM is configured with:
    - `runStrategy: Always` (this is what tells the cluster to restart the VM if it stops unexpectedly)
    - `evictionStrategy: LiveMigrate`
5. Click "Customize VirtualMachine" to edit the details before creating

### Add a Data Disk

6. Click on the "Disks" tab
7. Click "Add disk"
8. Configure the data disk:
    - Name: `data-disk`
    - Source: Blank
    - Size: 10 GiB
    - Type: Disk
    - StorageClass: your RWX-capable StorageClass
    - Access Mode: ReadWriteMany (RWX)

  !!! warning
      Both the root disk and the data disk must use RWX access mode for failover to work. If either disk is RWO, the VM cannot start on a new node until the old node's lease expires (6+ minutes).

9. Click Add
10. Also verify the root disk is using RWX access mode — edit it if necessary

### Start the VM

11. Click "Create VirtualMachine"
12. Wait for the VM status to show "Running"

## Verify the VM is Running

13. From the CLI, confirm the VM is running and note which node it is on:

  ```bash
  oc get vmi failover-test-vm -o wide
  ```

  The `NODE` column shows where the VM is currently scheduled.

14. Check the IP address assigned to the VM via IPAM. This IP is assigned by the CUDN (ClusterUserDefinedNetwork) and persists with the VM across node migrations and failovers:

  ```bash
  oc get vmi failover-test-vm -o jsonpath='{.status.interfaces}' | jq
  ```

  Record the IP address — you will verify it stays the same after failover.

15. Optionally, open the VM console from the WebUI to confirm the guest OS is up:
    - Virtualization -> VirtualMachines -> click `failover-test-vm` -> Console tab

## Simulate Node Failure

16. Record the node name where the VM is running:

  ```bash
  NODE=$(oc get vmi failover-test-vm -o jsonpath='{.status.nodeName}')
  echo "VM is on node: $NODE"
  ```

17. Start a timer and then restart the node to simulate a failure:

  ```bash
  date +%T && oc debug node/$NODE -- chroot /host systemctl reboot
  ```

  !!! note
      This simulates an unexpected node reboot. In a real failure scenario (power loss, kernel panic), the node would simply stop responding without a graceful shutdown.

## Watch the Failover

18. Immediately watch the VM instance for changes:

  ```bash
  oc get vmi failover-test-vm -w
  ```

  You should see the following sequence:
    - VM status remains `Running` initially (node hasn't been marked unhealthy yet)
    - After ~50s: node is marked `NotReady`
    - After ~80s: NHC creates a `SelfNodeRemediation` CR
    - After ~85-90s: node gets the `out-of-service` taint, pods are deleted
    - After ~100-120s: VM restarts on a different node

19. Once the VM shows `Running` again, check the timestamp:

  ```bash
  date +%T
  oc get vmi failover-test-vm -o wide
  ```

  The `NODE` column should show a different node than before.

## Verify the Failover

20. Confirm the VM is fully running on the new node:

  ```bash
  oc get vmi failover-test-vm -o jsonpath='{.status.phase}'
  ```

  Should output: `Running`

21. Verify the IP address followed the VM to the new node:

  ```bash
  oc get vmi failover-test-vm -o jsonpath='{.status.interfaces}' | jq
  ```

  The IP address should be **identical** to what was recorded before the failover. This is because the CUDN with persistent IPAM allocates the IP to the VM itself (not the node), so when the VM restarts on a different node, it retains the same IP. Clients connecting to this IP will be able to reach the VM on its new node without any DNS or configuration changes.

22. Check the data disk is still attached:

  ```bash
  oc get vmi failover-test-vm -o jsonpath='{.spec.volumes[*].name}'
  ```

23. Open the VM console from the WebUI to confirm the guest OS has booted:
    - Virtualization -> VirtualMachines -> click `failover-test-vm` -> Console tab
    - Login and verify the data disk is mounted (if it was mounted in the guest)
    - Run `ip addr` inside the guest to confirm the IP matches

24. Review the remediation events:

  ```bash
  oc get selfnoderemediation -A
  oc get events -n openshift-workload-availability --sort-by='.lastTimestamp'
  ```

## Expected Timeline

| Time    | Event                                                    |
| ------- | -------------------------------------------------------- |
| T+0s    | Node reboots — stops responding                          |
| T+~50s  | API server marks node `Ready=Unknown`                    |
| T+~80s  | NHC threshold (30s) breached, remediation CR created     |
| T+~85s  | SNR applies `out-of-service` taint                       |
| T+~90s  | Pods force-deleted, volumes detached                     |
| T+~100s | New VMI scheduled on healthy node, storage attached      |
| T+~120s | VM fully running on new node                             |

## Cleanup

25. Delete the test VM:

  ```bash
  oc delete vm failover-test-vm
  ```

26. Wait for the rebooted node to come back and verify it rejoins the cluster:

  ```bash
  oc get nodes -w
  ```

  The node should return to `Ready` status after it finishes rebooting.

!!! tip
    If the failover took significantly longer than 120 seconds, check:

    - Storage access mode (must be RWX)
    - NHC `unhealthyConditions.duration` is set to `30s`
    - Self Node Remediation pods are running on all nodes: `oc get pods -n openshift-workload-availability`
    - Hardware watchdog is available: `oc debug node/<node> -- chroot /host ls /dev/watchdog*`
