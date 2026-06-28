# Container Failover Test

This guide walks through testing container workload failover by deploying a sample application with multiple replicas, simulating a node failure, and verifying the pods are rescheduled to healthy nodes. This assumes [Workload Availability](../post-installation/workload-availability.md) is fully configured with the 120-second failover settings.

## Prerequisites

- Workload Availability operators installed (NHC, SNR, Descheduler)
- At least 3 worker nodes
- A default StorageClass available (for testing with persistent volumes)

## Deploy a Sample Application

1. Create a namespace for the test:

  ```bash
  oc new-project failover-test
  ```

2. Deploy a sample application with multiple replicas and a pod anti-affinity rule to spread pods across nodes:

  ```yaml
  apiVersion: apps/v1
  kind: Deployment
  metadata:
    name: failover-test-app
    namespace: failover-test
  spec:
    replicas: 3
    selector:
      matchLabels:
        app: failover-test
    template:
      metadata:
        labels:
          app: failover-test
      spec:
        affinity:
          podAntiAffinity:
            preferredDuringSchedulingIgnoredDuringExecution:
              - weight: 100
                podAffinityTerm:
                  labelSelector:
                    matchLabels:
                      app: failover-test
                  topologyKey: kubernetes.io/hostname
        containers:
          - name: app
            image: registry.redhat.io/ubi9/httpd-24:latest
            ports:
              - containerPort: 8080
            resources:
              requests:
                memory: "128Mi"
                cpu: "100m"
              limits:
                memory: "256Mi"
                cpu: "200m"
  ```

  ```bash
  oc apply -f failover-test-app.yaml
  ```

3. Create a Service to front the application:

  ```bash
  oc expose deployment failover-test-app --port=8080
  oc expose service failover-test-app
  ```

## Verify the Deployment

4. Confirm all 3 replicas are running and distributed across different nodes:

  ```bash
  oc get pods -o wide -n failover-test
  ```

  You should see pods on 3 different nodes due to the anti-affinity rule.

5. Record which pods are on which nodes:

  ```bash
  oc get pods -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName,IP:.status.podIP -n failover-test
  ```

6. Verify the application is responding through the Service:

  ```bash
  ROUTE=$(oc get route failover-test-app -o jsonpath='{.spec.host}')
  curl -s http://$ROUTE | head -5
  ```

## Simulate Node Failure

7. Pick one of the nodes that has a pod running on it:

  ```bash
  NODE=$(oc get pods -n failover-test -o jsonpath='{.items[0].spec.nodeName}')
  echo "Targeting node: $NODE"
  ```

8. Record the pod on that node:

  ```bash
  oc get pods -n failover-test --field-selector spec.nodeName=$NODE
  ```

9. Start a timer and reboot the node to simulate a failure:

  ```bash
  date +%T && oc debug node/$NODE -- chroot /host systemctl reboot
  ```

## Watch the Failover

10. Watch the pods for changes:

  ```bash
  oc get pods -o wide -n failover-test -w
  ```

  You should see the following sequence:
    - Pods on the failed node remain in `Running` state initially
    - After ~50s: node is marked `NotReady`
    - After ~80s: NHC creates a `SelfNodeRemediation` CR
    - After ~85s: `out-of-service` taint is applied, pods are force-deleted
    - After ~90s: new pod is scheduled on a healthy node and starts

11. Once the replacement pod shows `Running`, check the timestamp:

  ```bash
  date +%T
  oc get pods -o wide -n failover-test
  ```

  You should see 3 pods running again, with the replacement on a different node.

## Verify the Failover

12. Confirm all replicas are back to Running:

  ```bash
  oc get deployment failover-test-app -n failover-test
  ```

  The `AVAILABLE` count should be back to `3`.

13. Verify the Service is still responding without interruption:

  ```bash
  curl -s http://$ROUTE | head -5
  ```

  Because the Service load balances across all healthy pods, the remaining 2 replicas continued serving traffic during the failover. Once the 3rd pod is rescheduled, full capacity is restored.

14. Check which nodes are now hosting pods:

  ```bash
  oc get pods -o custom-columns=NAME:.metadata.name,NODE:.spec.nodeName,IP:.status.podIP -n failover-test
  ```

15. Review the remediation events:

  ```bash
  oc get selfnoderemediation -A
  oc get events -n failover-test --sort-by='.lastTimestamp'
  ```

## Key Differences from VM Failover

| Aspect             | Container Pods                                        | Virtual Machines                                  |
| ------------------ | ----------------------------------------------------- | ------------------------------------------------- |
| Restart behavior   | New pod created by Deployment controller              | New VMI created by virt-controller                |
| Downtime           | Zero (other replicas keep serving)                    | ~120s (single instance restarts)                  |
| IP persistence     | New pod gets a new IP (Service abstracts this)        | Same IP via CUDN persistent IPAM                  |
| Storage            | StatefulSet PVCs reattach; Deployment PVCs are fresh  | RWX disks reattach to new node                    |
| Scaling            | Multiple replicas provide built-in HA                 | Single instance, relies on failover               |

!!! info "Why Containers Recover Faster"
    With multiple replicas behind a Service, container workloads experience **zero downtime** from the client's perspective during a node failure. The Service immediately stops routing to the unavailable pod, and the remaining replicas handle all traffic. The Deployment controller then creates a replacement pod on a healthy node to restore full capacity — but the application was never actually "down."

## Test with a StatefulSet (Persistent Storage)

To test failover with persistent volumes, deploy a StatefulSet instead:

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: failover-test-stateful
  namespace: failover-test
spec:
  replicas: 3
  serviceName: failover-test-stateful
  selector:
    matchLabels:
      app: failover-test-stateful
  template:
    metadata:
      labels:
        app: failover-test-stateful
    spec:
      containers:
        - name: app
          image: registry.redhat.io/ubi9/httpd-24:latest
          ports:
            - containerPort: 8080
          volumeMounts:
            - name: data
              mountPath: /var/data
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 1Gi
```

!!! warning "RWO StatefulSet Failover"
    StatefulSet pods using RWO volumes depend on the `out-of-service` taint to force-detach the volume from the failed node. Without Workload Availability (NHC + SNR), Kubernetes would wait for the node lease to expire (6+ minutes) before allowing the volume to attach elsewhere.

## Cleanup

16. Delete the test resources:

  ```bash
  oc delete project failover-test
  ```

17. Wait for the rebooted node to come back:

  ```bash
  oc get nodes -w
  ```
