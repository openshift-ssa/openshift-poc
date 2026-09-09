# Example Container Workloads

These workloads exercise different cluster capabilities — networking, storage, builds, operators, and service mesh — using lightweight deployments suitable for a POC. Run the ones relevant to your POC scope; you do not need to deploy all of them.

| Workload | What It Validates | Prerequisites |
|----------|-------------------|---------------|
| [Hello World Web Server](./hello-world-web-server.md) | Routes, image pull, basic scheduling | None |
| [Spring Pet Clinic](./spring-petclinic.md) | Java app with web UI, image streams | None |
| [Kafka Cluster with Strimzi](./kafka-strimzi.md) | Operator lifecycle, stateful workloads | Persistent storage |
| [Source-to-Image (S2I) Build](./s2i-build.md) | Build pipeline, Git integration | None |
| [PostgreSQL with Persistent Storage](./postgresql.md) | CSI storage, stateful database | Persistent storage |
| [PVC Read-Back Test](./pvc-readback.md) | CSI write/read verification | Persistent storage |
| [Bookinfo (Service Mesh)](./bookinfo.md) | Traffic management, mTLS, observability | [Service Mesh](../../configure-the-cluster/service-mesh.md) |

!!! tip "Recommended Starting Point"
    Start with **Hello World Web Server** to confirm basic cluster functionality, then **PostgreSQL** or **PVC Read-Back** to validate storage, and add others based on your POC goals.
