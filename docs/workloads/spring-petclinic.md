# Spring Pet Clinic

The [Spring Pet Clinic](https://github.com/spring-projects/spring-petclinic) is a sample Java application built with Spring Boot. It demonstrates a typical multi-tier web application with a web UI, REST API, and database backend.

## Deploy with Source-to-Image (S2I)

1. Create a namespace:

```bash
  oc new-project petclinic
```

2. Deploy the application using S2I:

```bash
  oc new-app --image-stream="openshift/java:openjdk-17-ubi8" \
    https://github.com/spring-projects/spring-petclinic.git \
    --name=petclinic
```

  This builds the application from source using the OpenShift Java builder image.

3. Watch the build progress:

```bash
  oc logs -f buildconfig/petclinic
```

4. Expose the application with a Route:

```bash
  oc expose service petclinic
```

5. Verify the deployment:

```bash
  oc get pods -n petclinic
  ROUTE=$(oc get route petclinic -o jsonpath='{.spec.host}')
  echo "Application available at: http://$ROUTE"
```

## Deploy from Container Image

Alternatively, deploy a pre-built image:

1. Create a namespace:

```bash
  oc new-project petclinic
```

2. Create the Deployment:

```yaml
  apiVersion: apps/v1
  kind: Deployment
  metadata:
    name: petclinic
    namespace: petclinic
    labels:
      app: petclinic
  spec:
    replicas: 1
    selector:
      matchLabels:
        app: petclinic
    template:
      metadata:
        labels:
          app: petclinic
      spec:
        containers:
          - name: petclinic
            image: docker.io/springcommunity/spring-framework-petclinic:latest
            ports:
              - containerPort: 8080
            resources:
              requests:
                memory: "512Mi"
                cpu: "250m"
              limits:
                memory: "1Gi"
                cpu: "500m"
            readinessProbe:
              httpGet:
                path: /
                port: 8080
              initialDelaySeconds: 30
              periodSeconds: 10
            livenessProbe:
              httpGet:
                path: /
                port: 8080
              initialDelaySeconds: 60
              periodSeconds: 10
```

```bash
  oc apply -f petclinic-deployment.yaml
```

3. Create a Service and Route:

```bash
  oc expose deployment petclinic --port=8080
  oc expose service petclinic
```

4. Verify it's running:

```bash
  oc get pods -n petclinic
  ROUTE=$(oc get route petclinic -o jsonpath='{.spec.host}')
  curl -s -o /dev/null -w "%{http_code}" http://$ROUTE
```

  You should see HTTP status `200` once the application has started.

## Deploy with a PostgreSQL Database

By default, Pet Clinic uses an in-memory H2 database. For a persistent setup, deploy with PostgreSQL:

1. Deploy PostgreSQL:

```bash
  oc new-app --name=petclinic-db \
    -e POSTGRESQL_USER=petclinic \
    -e POSTGRESQL_PASSWORD=petclinic \
    -e POSTGRESQL_DATABASE=petclinic \
    postgresql:latest
```

2. Deploy Pet Clinic with the PostgreSQL profile:

```bash
  oc new-app --name=petclinic \
    -e SPRING_PROFILES_ACTIVE=postgres \
    -e POSTGRES_URL=jdbc:postgresql://petclinic-db:5432/petclinic \
    -e POSTGRES_USER=petclinic \
    -e POSTGRES_PASS=petclinic \
    java~https://github.com/spring-projects/spring-petclinic.git
```

3. Expose and verify:

```bash
  oc expose service petclinic
  ROUTE=$(oc get route petclinic -o jsonpath='{.spec.host}')
  echo "Application available at: http://$ROUTE"
```

## Cleanup

```bash
oc delete project petclinic
```
