# Monitoring and Alerting

[Red Hat OpenShift Monitoring Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/monitoring/index)

OpenShift ships with a pre-configured monitoring stack based on Prometheus, Alertmanager, and Grafana (read-only dashboards in the web console). The stack is installed automatically — this page covers how to verify it, enable user workload monitoring, and configure alert routing.

## Verify the Built-In Monitoring Stack

The cluster monitoring operator deploys Prometheus, Alertmanager, and related components into `openshift-monitoring`:

```bash
oc get pods -n openshift-monitoring
```

All pods should be `Running`. Key components:

| Component | Purpose |
|-----------|---------|
| `prometheus-k8s-*` | Scrapes metrics from cluster components and stores time-series data |
| `alertmanager-main-*` | Routes alerts to receivers (email, Slack, PagerDuty, webhooks) |
| `thanos-querier-*` | Provides a unified query endpoint across Prometheus instances |
| `kube-state-metrics-*` | Exposes Kubernetes object state as metrics |
| `node-exporter-*` | Exposes node-level hardware and OS metrics (one per node) |

## Access Monitoring Dashboards

1. Go to **Observe** → **Dashboards** in the web console
2. Select a dashboard from the dropdown (e.g., **Kubernetes / Compute Resources / Cluster**)
3. Dashboards are read-only and automatically populated

To query metrics directly:

1. Go to **Observe** → **Metrics**
2. Enter a PromQL query, for example:

  ```promql
  sum(rate(container_cpu_usage_seconds_total{namespace!=""}[5m])) by (namespace)
  ```

## View Active Alerts

1. Go to **Observe** → **Alerting** in the web console
2. Review firing and pending alerts
3. Common alerts to watch during a POC:

| Alert | Meaning |
|-------|---------|
| `ClusterOperatorDegraded` | A ClusterOperator is not functioning correctly |
| `KubePodNotReady` | Pods are not reaching Ready state |
| `NodeNotReady` | A node has left the Ready state |
| `etcdHighCommitDurations` | etcd is slow — possible disk or network issue |
| `KubePersistentVolumeFillingUp` | A PVC is running low on space |

From the CLI:

```bash
oc get prometheusrule -n openshift-monitoring
oc -n openshift-monitoring exec -c prometheus prometheus-k8s-0 -- \
  promtool query instant http://localhost:9090 'ALERTS{alertstate="firing"}'
```

## Enable User Workload Monitoring

By default, Prometheus only monitors OpenShift infrastructure components. To monitor application workloads deployed by users, enable user workload monitoring:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-monitoring-config
  namespace: openshift-monitoring
data:
  config.yaml: |
    enableUserWorkload: true
```

```bash
oc apply -f cluster-monitoring-config.yaml
```

Verify the user workload monitoring components start:

```bash
oc get pods -n openshift-user-workload-monitoring
```

You should see `prometheus-user-workload-*` and `thanos-ruler-user-workload-*` pods.

!!! note
    User workload monitoring creates a separate Prometheus instance in `openshift-user-workload-monitoring`. Applications expose metrics via `ServiceMonitor` or `PodMonitor` CRs in their own namespaces.

## Configure Alertmanager (Alert Routing)

The default Alertmanager receives alerts but does not send notifications anywhere. Configure receivers to route alerts to your team.

### View the Current Alertmanager Config

```bash
oc -n openshift-monitoring get secret alertmanager-main \
  -o jsonpath='{.data.alertmanager\.yaml}' | base64 -d
```

### Configure a Receiver

Create an Alertmanager config with a receiver. This example sends critical alerts to a webhook:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: alertmanager-main
  namespace: openshift-monitoring
stringData:
  alertmanager.yaml: |
    global:
      resolve_timeout: 5m
    route:
      group_by: ['namespace', 'alertname']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 12h
      receiver: default
      routes:
        - match:
            severity: critical
          receiver: webhook-critical
    receivers:
      - name: default
      - name: webhook-critical
        webhook_configs:
          - url: '{{ webhook_url }}'
            send_resolved: true
```

```bash
oc apply -f alertmanager-config.yaml
```

### Other Receiver Types

| Receiver | Config Key | Use Case |
|----------|-----------|----------|
| Email | `email_configs` | Send alerts to a team inbox |
| Slack | `slack_configs` | Post alerts to a Slack channel |
| PagerDuty | `pagerduty_configs` | Trigger incidents for on-call rotation |
| Webhook | `webhook_configs` | Forward to any HTTP endpoint |

See the [Alertmanager configuration documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/monitoring/configuring-alert-notifications) for full receiver configuration options.

## Configure Persistent Storage for Metrics

By default, Prometheus uses `emptyDir` volumes — metrics are lost on pod restart. For a POC, configure persistent storage:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cluster-monitoring-config
  namespace: openshift-monitoring
data:
  config.yaml: |
    enableUserWorkload: true
    prometheusK8s:
      retention: 15d
      volumeClaimTemplate:
        spec:
          storageClassName: {{ storage_class }}
          resources:
            requests:
              storage: 50Gi
    alertmanagerMain:
      volumeClaimTemplate:
        spec:
          storageClassName: {{ storage_class }}
          resources:
            requests:
              storage: 5Gi
```

```bash
oc apply -f cluster-monitoring-config.yaml
```

!!! tip
    `retention: 15d` keeps 15 days of metrics. Adjust based on your POC duration and available storage. For a typical POC, 50Gi with 15-day retention is sufficient.

## Create a Custom Alert (Optional)

Demonstrate custom alerting by creating a `PrometheusRule` that fires when a namespace has no running pods:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: poc-example-alerts
  namespace: openshift-monitoring
spec:
  groups:
    - name: poc.rules
      rules:
        - alert: HighNodeCPU
          expr: instance:node_cpu_utilisation:rate5m > 0.9
          for: 10m
          labels:
            severity: warning
          annotations:
            summary: "Node {{ "{{ $labels.instance }}" }} CPU usage above 90%"
            description: "Node {{ "{{ $labels.instance }}" }} has had CPU utilisation above 90% for more than 10 minutes."
```

```bash
oc apply -f poc-alerts.yaml
```

Verify the rule is loaded:

```bash
oc get prometheusrule poc-example-alerts -n openshift-monitoring
```

Check in the web console under **Observe** → **Alerting** → **Alerting Rules** to see the new rule.

## Verify

1. **Dashboards**: Go to **Observe** → **Dashboards** — confirm data is populating
2. **Metrics**: Go to **Observe** → **Metrics** — run `up` and verify targets are scraped
3. **Alerts**: Go to **Observe** → **Alerting** — confirm no unexpected critical alerts
4. **Storage**: Check Prometheus PVCs are bound:

  ```bash
  oc get pvc -n openshift-monitoring
  ```
