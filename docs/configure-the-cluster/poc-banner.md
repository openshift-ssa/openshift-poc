# POC Banner

Mark the OpenShift web console with a banner to ensure everyone knows what environment they are in.

1. Go to the WebUI and in the top right hand corner, click on the circle plus icon
2. Select Import YAML
3. Paste the YAML below

```yaml
apiVersion: console.openshift.io/v1
kind: ConsoleNotification
metadata:
  name: poc-notification
spec:
  text: POC Environment
  location: BannerTop
  color: '#ffffff'
  backgroundColor: '#aa4f13'
```
