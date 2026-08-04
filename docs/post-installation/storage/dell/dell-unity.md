# Dell Unity XT (iSCSI)

[Dell CSI Driver for Unity XT](https://dell.github.io/csm-docs/docs/csidriver/installation/operator/unity/) | [CSM Operator](https://dell.github.io/csm-docs/docs/deployment/csmoperator/)

This guide installs the Dell CSI driver for Unity XT via the Container Storage Modules (CSM) Operator on OpenShift {{ ocp_version }}. It uses CSM Operator v1.12.x (CSM 1.17.x) with the Unity driver `configVersion: v2.15.0`.

## Step 1 — Array-Side Prep (Unisphere)

Before touching the cluster, configure the Unity XT array:

1. Configure iSCSI interfaces on both SPs (SPA + SPB) on your storage VLAN
2. Create a storage pool — note the pool name/ID
3. Confirm the Unisphere management IP is reachable over IPv4 from the cluster nodes (the driver is IPv4-only)
4. If running jumbo frames, MTU 9000 must match end-to-end (array ports, switches, node NICs)

Collect the **array serial** (`APM00...`) and **pool name** — both are required below.

## Step 2 — Node Prep (MachineConfigs)

RHCOS does not ship with an iSCSI initiator name, and Unity requires multipath. Apply all three MachineConfigs, then wait for the worker nodes to reboot.

### 2a. Generate iSCSI InitiatorName

Creates `/etc/iscsi/initiatorname.iscsi` if missing:

```bash
cat << 'EOF' | oc apply -f -
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfig
metadata:
  name: 99-worker-iscsi-initiatorname
  labels:
    machineconfiguration.openshift.io/role: worker
spec:
  config:
    ignition:
      version: 3.4.0
    storage:
      files:
        - path: /usr/local/bin/gen-initiatorname.sh
          mode: 0755
          overwrite: true
          contents:
            source: data:text/plain;base64,IyEvYmluL3NoCmlmIFsgISAtZiAvZXRjL2lzY3NpL2luaXRpYXRvcm5hbWUuaXNjc2kgXTsgdGhlbgogICAgZWNobyAiSW5pdGlhdG9yTmFtZT0kKC91c3Ivc2Jpbi9pc2NzaS1pbmFtZSkiID4gL2V0Yy9pc2NzaS9pbml0aWF0b3JuYW1lLmlzY3NpCmZpCg==
    systemd:
      units:
        - name: custom-iscsi-initiatorname.service
          enabled: true
          contents: |
            [Unit]
            Description=Generate iSCSI InitiatorName if missing
            Before=iscsid.service iscsi.service
            ConditionPathExists=!/etc/iscsi/initiatorname.iscsi
            [Service]
            Type=oneshot
            RemainAfterExit=yes
            ExecStart=/usr/local/bin/gen-initiatorname.sh
            [Install]
            WantedBy=multi-user.target
EOF
```

### 2b. Enable iscsid

```bash
cat << 'EOF' | oc apply -f -
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfig
metadata:
  name: 99-worker-iscsid-enable
  labels:
    machineconfiguration.openshift.io/role: worker
spec:
  config:
    ignition:
      version: 3.4.0
    systemd:
      units:
        - name: iscsid.service
          enabled: true
EOF
```

### 2c. Multipath Configuration

Enables `multipathd` with Dell Unity defaults:

```bash
cat << 'EOF' | oc apply -f -
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfig
metadata:
  name: 99-worker-multipath
  labels:
    machineconfiguration.openshift.io/role: worker
spec:
  config:
    ignition:
      version: 3.4.0
    storage:
      files:
        - path: /etc/multipath.conf
          mode: 0644
          overwrite: true
          contents:
            source: data:text/plain;base64,ZGVmYXVsdHMgewogICAgdXNlcl9mcmllbmRseV9uYW1lcyB5ZXMKICAgIGZpbmRfbXVsdGlwYXRocyB5ZXMKICAgIHBvbGxpbmdfaW50ZXJ2YWwgNQp9CmJsYWNrbGlzdCB7Cn0K
    systemd:
      units:
        - name: multipathd.service
          enabled: true
EOF
```

### Wait for Rollout

Workers reboot serially. Wait for the MachineConfigPool to finish:

```bash
oc get mcp worker -w
```

All pools should show `UPDATED=True`, `UPDATING=False`, `DEGRADED=False`.

### Spot-Check a Worker

```bash
W=$(oc get nodes -l node-role.kubernetes.io/worker -o name | head -1)
oc debug $W -- chroot /host cat /etc/iscsi/initiatorname.iscsi
oc debug $W -- chroot /host systemctl is-active iscsid multipathd
```

!!! warning "Order matters"
    Step 2 must fully complete before deploying the driver in Step 6. If node pods CrashLoop with initiator name errors, the MachineConfig rollout was not finished before the driver was deployed.

## Step 3 — Namespaces

```bash
cat << 'EOF' | oc apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: dell-csm-operator
  labels:
    pod-security.kubernetes.io/enforce: privileged
    pod-security.kubernetes.io/audit: privileged
    pod-security.kubernetes.io/warn: privileged
---
apiVersion: v1
kind: Namespace
metadata:
  name: unity
  labels:
    pod-security.kubernetes.io/enforce: privileged
    pod-security.kubernetes.io/audit: privileged
    pod-security.kubernetes.io/warn: privileged
EOF
```

## Step 4 — Install the CSM Operator

```bash
cat << 'EOF' | oc apply -f -
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: dell-csm-operator
  namespace: dell-csm-operator
spec: {}
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: dell-csm-operator-certified
  namespace: dell-csm-operator
spec:
  channel: stable
  name: dell-csm-operator-certified
  source: certified-operators
  sourceNamespace: openshift-marketplace
  installPlanApproval: Manual
EOF
```

Approve the install plan and confirm the CSV:

```bash
oc get installplan -n dell-csm-operator
oc patch installplan <name> -n dell-csm-operator --type merge -p '{"spec":{"approved":true}}'

oc get csv -n dell-csm-operator          # Phase: Succeeded
oc get crd containerstoragemodules.storage.dell.com   # CRD exists
```

## Step 5 — Credentials Secret

Replace the array serial, Unisphere endpoint (IPv4), and password:

```bash
cat << 'EOF' > /tmp/unity-creds.yaml
storageArrayList:
  - arrayId: "APM00XXXXXXXXX"
    username: "admin"
    password: "YourPassword"
    endpoint: "https://10.0.0.10/"
    skipCertificateValidation: true
    isDefault: true
EOF

oc create secret generic unity-creds -n unity --from-file=config=/tmp/unity-creds.yaml
rm -f /tmp/unity-creds.yaml
```

## Step 6 — Deploy the Driver (ContainerStorageModule CR)

```bash
cat << 'EOF' | oc apply -f -
apiVersion: storage.dell.com/v1
kind: ContainerStorageModule
metadata:
  name: unity
  namespace: unity
spec:
  driver:
    csiDriverType: "unity"
    configVersion: v2.15.0
    replicas: 2
    authSecret: unity-creds
    common:
      image: "quay.io/dell/container-storage-modules/csi-unity:v2.15.0"
      imagePullPolicy: IfNotPresent
      envs:
        - name: X_CSI_UNITY_ALLOW_MULTI_POD_ACCESS
          value: "false"
        - name: X_CSI_HEALTH_MONITOR_ENABLED
          value: "false"
        - name: X_CSI_UNITY_AUTOPROBE
          value: "true"
        - name: X_CSI_UNITY_SKIP_CERTIFICATE_VALIDATION
          value: "true"
        - name: CERT_SECRET_COUNT
          value: "0"
    controller:
      envs:
        - name: X_CSI_HEALTH_MONITOR_ENABLED
          value: "false"
    node:
      envs:
        - name: X_CSI_HEALTH_MONITOR_ENABLED
          value: "false"
EOF
```

!!! tip
    If the operator rejects `configVersion`, check its logs for the version it validates: `oc get csm unity -n unity -o yaml`. Set both `configVersion` and the image tag to the version the operator expects.

## Step 7 — StorageClass and VolumeSnapshotClass

Replace `arrayId` and `storagepool` with your values from Step 1.

!!! warning "ArrayID Must Be Lowercase"
    The `arrayId` value in the StorageClass **must be lowercase**. The Unity CSI driver labels worker nodes with a lowercase ArrayID in the topology key (e.g. `csi-unity.dellemc.com/apx00241102102-iscsi=true`). If the StorageClass specifies it in uppercase (e.g. `APX00241102102`), the topology constraint will not match and PVCs will stay stuck in `Pending`. Kubernetes topology labels are case-sensitive.

```bash
cat << 'EOF' | oc apply -f -
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: unity-iscsi
provisioner: csi-unity.dellemc.com
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
parameters:
  protocol: iSCSI
  arrayId: "apm00xxxxxxxxx"
  storagepool: "pool_1"
  thinProvisioned: "true"
  isDataReductionEnabled: "false"
  csi.storage.k8s.io/fstype: "ext4"
---
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: unity-snapclass
driver: csi-unity.dellemc.com
deletionPolicy: Delete
EOF
```

## Step 8 — Verify

```bash
oc get csm -n unity unity -o wide          # State: Succeeded
oc get pods -n unity                       # controller (x2) + node pods Running
oc get csinode -o wide                     # each worker lists csi-unity.dellemc.com
oc get sc unity-iscsi
```

## Step 9 — Smoke Test

```bash
cat << 'EOF' | oc apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: unity-test
  namespace: unity
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: unity-iscsi
  resources:
    requests:
      storage: 5Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: unity-test-pod
  namespace: unity
spec:
  containers:
    - name: app
      image: registry.access.redhat.com/ubi9/ubi-minimal
      command: ["sh", "-c", "echo hello > /data/test && sleep 3600"]
      volumeMounts:
        - name: vol
          mountPath: /data
  volumes:
    - name: vol
      persistentVolumeClaim:
        claimName: unity-test
EOF
```

Confirm the PVC binds and the pod can write:

```bash
oc get pvc -n unity unity-test -w              # -> Bound
oc exec -n unity unity-test-pod -- cat /data/test   # -> hello
```

Clean up:

```bash
oc delete pod unity-test-pod -n unity
oc delete pvc unity-test -n unity
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Node pods CrashLoop with initiator errors | MachineConfig not finished before driver deployed | Wait for `oc get mcp worker` to show `UPDATED=True`, then delete the node pods to restart them |
| PVC stuck in Pending | Wrong `arrayId` or `storagepool` in StorageClass | Check controller pod logs: `oc logs -n unity -l app=unity-controller --tail=50` |
| PVC stuck in Pending with topology mismatch | `arrayId` in StorageClass is uppercase but the driver labels nodes with lowercase | Change `arrayId` in the StorageClass to lowercase to match the node topology labels (e.g. `apm00xxxxxxxxx` not `APM00XXXXXXXXX`) |
| `configVersion` rejected | Operator/driver version mismatch | Check `oc get csm unity -n unity -o yaml` for the expected version |
| iSCSI login failures | Array iSCSI interfaces not on the same VLAN as nodes | Verify SPA/SPB iSCSI IPs are reachable from worker nodes |
