# Kafka Cluster with Strimzi

[Strimzi](https://strimzi.io/) provides a way to run Apache Kafka on OpenShift via the Strimzi Cluster Operator. It manages Kafka clusters, topics, users, and connectors using custom resources.

## Prerequisites

- Cluster-admin access (for installing the operator)
- Sufficient cluster resources (minimum 3 broker nodes recommended for production)

## Install the Strimzi Operator

1. Create a namespace for the Kafka cluster:

  ```bash
  oc new-project kafka
  ```

2. Install Strimzi from OperatorHub:

  ```bash
  cat <<EOF | oc apply -f -
  apiVersion: operators.coreos.com/v1alpha1
  kind: Subscription
  metadata:
    name: strimzi-kafka-operator
    namespace: openshift-operators
  spec:
    channel: stable
    name: strimzi-kafka-operator
    source: community-operators
    sourceNamespace: openshift-marketplace
  EOF
  ```

3. Wait for the operator to be ready:

  ```bash
  oc get csv -n openshift-operators | grep strimzi
  ```

  The phase should show `Succeeded`.

## Deploy a Kafka Cluster

1. Create a Kafka cluster with 3 brokers and 3 ZooKeeper nodes:

  ```yaml
  apiVersion: kafka.strimzi.io/v1beta2
  kind: Kafka
  metadata:
    name: my-cluster
    namespace: kafka
  spec:
    kafka:
      version: 3.7.0
      replicas: 3
      listeners:
        - name: plain
          port: 9092
          type: internal
          tls: false
        - name: tls
          port: 9093
          type: internal
          tls: true
      config:
        offsets.topic.replication.factor: 3
        transaction.state.log.replication.factor: 3
        transaction.state.log.min.isr: 2
        default.replication.factor: 3
        min.insync.replicas: 2
      storage:
        type: persistent-claim
        size: 10Gi
      resources:
        requests:
          memory: "2Gi"
          cpu: "500m"
        limits:
          memory: "4Gi"
          cpu: "1"
    zookeeper:
      replicas: 3
      storage:
        type: persistent-claim
        size: 5Gi
      resources:
        requests:
          memory: "1Gi"
          cpu: "250m"
        limits:
          memory: "2Gi"
          cpu: "500m"
    entityOperator:
      topicOperator: {}
      userOperator: {}
  ```

  ```bash
  oc apply -f kafka-cluster.yaml
  ```

2. Wait for the cluster to become ready:

  ```bash
  oc wait kafka/my-cluster --for=condition=Ready --timeout=300s -n kafka
  ```

3. Verify all pods are running:

  ```bash
  oc get pods -n kafka
  ```

  You should see pods for ZooKeeper, Kafka brokers, and the Entity Operator.

## Create a Topic

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: KafkaTopic
metadata:
  name: my-topic
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  partitions: 3
  replicas: 3
  config:
    retention.ms: 604800000
```

```bash
oc apply -f kafka-topic.yaml
```

## Test with a Producer and Consumer

1. Start a console producer:

  ```bash
  oc run kafka-producer -ti \
    --image=quay.io/strimzi/kafka:latest-kafka-3.7.0 \
    --rm=true --restart=Never \
    -- bin/kafka-console-producer.sh \
    --bootstrap-server my-cluster-kafka-bootstrap:9092 \
    --topic my-topic
  ```

2. In a separate terminal, start a console consumer:

  ```bash
  oc run kafka-consumer -ti \
    --image=quay.io/strimzi/kafka:latest-kafka-3.7.0 \
    --rm=true --restart=Never \
    -- bin/kafka-console-consumer.sh \
    --bootstrap-server my-cluster-kafka-bootstrap:9092 \
    --topic my-topic \
    --from-beginning
  ```

## Expose Kafka Outside the Cluster (Optional)

To access Kafka from outside OpenShift, add a Route listener:

```yaml
apiVersion: kafka.strimzi.io/v1beta2
kind: Kafka
metadata:
  name: my-cluster
  namespace: kafka
spec:
  kafka:
    listeners:
      - name: external
        port: 9094
        type: route
        tls: true
```

Retrieve the bootstrap address:

```bash
oc get kafka my-cluster -n kafka -o jsonpath='{.status.listeners[?(@.name=="external")].bootstrapServers}'
```

## Cleanup

```bash
oc delete kafka my-cluster -n kafka
oc delete subscription strimzi-kafka-operator -n openshift-operators
oc delete project kafka
```
