# PostgreSQL with Persistent Storage

[RHEL 9 PostgreSQL 16](https://catalog.redhat.com/en/software/containers/rhel9/postgresql-16/65de09b1b5ff7744d1651928)

This example deploys PostgreSQL from the UBI-based `registry.redhat.io/rhel9/postgresql-16` image with a PersistentVolumeClaim (PVC). It validates that the CSI driver and StorageClass work end-to-end: stateful workloads, persistent storage, and data that survives pod restarts.

!!! note
    Distroless hardened images do not include a shell or `psql` client, so `oc rsh` into those images fails. This POC uses the UBI image so you can run the interactive checks below.

## Prerequisites

- [Storage](../../configure-the-cluster/storage/index.md) configured with a default StorageClass

## Deploy PostgreSQL

1. Create a namespace:

  ```bash
  oc new-project postgresql-demo
  ```

2. Create the PersistentVolumeClaim:

  ```yaml
  apiVersion: v1
  kind: PersistentVolumeClaim
  metadata:
    name: postgresql-data
    namespace: postgresql-demo
  spec:
    accessModes:
      - ReadWriteOnce
    resources:
      requests:
        storage: 10Gi
  ```

  ```bash
  oc apply -f postgresql-pvc.yaml
  ```

3. Create the Deployment:

  ```yaml
  apiVersion: apps/v1
  kind: Deployment
  metadata:
    name: postgresql
    namespace: postgresql-demo
    labels:
      app: postgresql
  spec:
    replicas: 1
    selector:
      matchLabels:
        app: postgresql
    strategy:
      type: Recreate
    template:
      metadata:
        labels:
          app: postgresql
      spec:
        containers:
          - name: postgresql
            image: registry.redhat.io/rhel9/postgresql-16
            ports:
              - containerPort: 5432
            env:
              - name: POSTGRESQL_USER
                value: demo
              - name: POSTGRESQL_PASSWORD
                value: demo123
              - name: POSTGRESQL_DATABASE
                value: sampledb
            resources:
              requests:
                memory: "256Mi"
                cpu: "250m"
              limits:
                memory: "512Mi"
                cpu: "500m"
            volumeMounts:
              - name: postgresql-data
                mountPath: /var/lib/pgsql/data
            readinessProbe:
              tcpSocket:
                port: 5432
              initialDelaySeconds: 5
              periodSeconds: 10
            livenessProbe:
              tcpSocket:
                port: 5432
              initialDelaySeconds: 30
              periodSeconds: 10
        volumes:
          - name: postgresql-data
            persistentVolumeClaim:
              claimName: postgresql-data
  ```

  ```bash
  oc apply -f postgresql-deployment.yaml
  ```

4. Create the Service:

  ```bash
  oc expose deployment postgresql --port=5432
  ```

5. Verify the PVC is bound and the pod is running:

  ```bash
  oc get pvc -n postgresql-demo
  oc get pods -n postgresql-demo
  ```

## Write Test Data

1. Connect to PostgreSQL and insert some data:

  ```bash
  oc rsh deployment/postgresql
  ```

  Inside the pod:

  ```sql
  psql -U demo -d sampledb
  CREATE TABLE demo (id serial PRIMARY KEY, message text, created_at timestamp DEFAULT now());
  INSERT INTO demo (message) VALUES ('Hello from OpenShift!');
  INSERT INTO demo (message) VALUES ('Persistent storage works.');
  SELECT * FROM demo;
  \q
  exit
  ```

## Test Persistence

1. Delete the pod (the Deployment will recreate it):

  ```bash
  oc delete pod -l app=postgresql -n postgresql-demo
  ```

2. Wait for the new pod to start:

  ```bash
  oc get pods -n postgresql-demo -w
  ```

3. Verify the data survived the pod restart:

  ```bash
  oc rsh deployment/postgresql
  ```

  ```sql
  psql -U demo -d sampledb
  SELECT * FROM demo;
  \q
  exit
  ```

  The rows inserted earlier should still be there, proving the PVC retained the data across pod recreation.

## What to Show in a Demo

- **PVC binding** — `oc get pvc` shows the claim bound to a PV provisioned by the CSI driver
- **Data persistence** — data survives pod deletion and recreation
- **Storage class in action** — the default StorageClass dynamically provisions the volume
- **Pod scheduling** — the pod is scheduled to a node where the volume is accessible
- **Stateful workloads** — OpenShift handles the same database workloads as traditional VMs

## Cleanup

```bash
oc delete project postgresql-demo
```
