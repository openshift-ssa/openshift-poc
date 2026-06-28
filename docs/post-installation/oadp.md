# OpenShift API for Data Protection (OADP)

[OADP Official Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/backup_and_restore/oadp-application-backup-and-restore)

OADP provides backup and restore capabilities for applications, virtual machines, and persistent volumes running on OpenShift. It is built on Velero and supports CSI snapshots, file system backups, and VM-aware backups via the kubevirt plugin.

## Prerequisites

- Object storage available (ODF NooBaa, AWS S3, or any S3-compatible endpoint)
- OpenShift Virtualization installed (if backing up VMs)
- Cluster administrator privileges

## Install the Operator via WebUI

1. Go to Ecosystem -> Software Catalog -> filter for "OADP" -> click the "OADP Operator" tile
2. Click Install
3. Leave all the defaults (installs to `openshift-adp` namespace) and click Install
4. Wait for the Operator to install

## Install the Operator via YAML

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-adp
---
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: openshift-adp
  namespace: openshift-adp
spec:
  targetNamespaces:
    - openshift-adp
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: redhat-oadp-operator
  namespace: openshift-adp
spec:
  channel: stable-1.5
  installPlanApproval: Automatic
  name: redhat-oadp-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
```

```bash
oc apply -f oadp-operator.yaml
```

Wait for the operator:

```bash
oc get csv -n openshift-adp -w
```

The `PHASE` should show `Succeeded`.

## Create the Object Storage Bucket

OADP requires an S3-compatible object storage bucket for backup data. If you have ODF with NooBaa available, create an ObjectBucketClaim:

1. Create the bucket:

  ```yaml
  apiVersion: objectbucket.io/v1alpha1
  kind: ObjectBucketClaim
  metadata:
    name: oadp-backup-bucket
    namespace: openshift-adp
  spec:
    bucketName: oadp-backup-bucket
    storageClassName: openshift-storage.noobaa.io
  ```

  ```bash
  oc apply -f oadp-bucket.yaml
  ```

2. Wait for the bucket to be bound:

  ```bash
  oc get obc oadp-backup-bucket -n openshift-adp
  ```

  The `PHASE` should show `Bound`.

3. Extract the credentials and create the cloud-credentials secret:

  ```bash
  ACCESS_KEY=$(oc get secret oadp-backup-bucket -n openshift-adp -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' | base64 -d)
  SECRET_KEY=$(oc get secret oadp-backup-bucket -n openshift-adp -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' | base64 -d)

  cat <<EOF > /tmp/credentials-velero
  [default]
  aws_access_key_id=$ACCESS_KEY
  aws_secret_access_key=$SECRET_KEY
  EOF

  oc create secret generic cloud-credentials \
    --from-file=cloud=/tmp/credentials-velero \
    -n openshift-adp

  rm /tmp/credentials-velero
  ```

## Create the DataProtectionApplication

4. Create the DPA to configure Velero with the required plugins:

  ```yaml
  apiVersion: oadp.openshift.io/v1alpha1
  kind: DataProtectionApplication
  metadata:
    name: dpa
    namespace: openshift-adp
  spec:
    configuration:
      velero:
        defaultPlugins:
          - kubevirt
          - openshift
          - csi
          - aws
        resourceTimeout: 10m
      nodeAgent:
        enable: true
        uploaderType: kopia
    backupLocations:
      - name: default
        velero:
          provider: aws
          default: true
          objectStorage:
            bucket: oadp-backup-bucket
            prefix: velero
          config:
            region: noobaa
            s3ForcePathStyle: "true"
            s3Url: https://s3-openshift-storage.apps.{{ cluster_name }}.{{ base_domain }}
            insecureSkipTLSVerify: "true"
          credential:
            name: cloud-credentials
            key: cloud
  ```

  !!! note "Plugin Descriptions"
      | Plugin     | Purpose                                                    |
      | ---------- | ---------------------------------------------------------- |
      | `kubevirt` | Required for backing up and restoring VirtualMachines      |
      | `openshift`| Required for OpenShift-specific resources (Routes, etc.)   |
      | `csi`      | Enables CSI volume snapshots for PVC backups               |
      | `aws`      | S3-compatible object storage provider (works with NooBaa)  |

  ```bash
  oc apply -f dpa.yaml
  ```

## Verify

```bash
oc get dpa -n openshift-adp
oc get backupstoragelocation -n openshift-adp
```

The BackupStorageLocation `PHASE` should show `Available`.

```bash
oc get pods -n openshift-adp
```

You should see Velero and node-agent pods running.
