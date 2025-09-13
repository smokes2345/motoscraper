# motoscraper

A rather dumb script to scrape signal metrics from my motorola MB7220 modem generated with, mostly, qwen3.

the pod manifest looks something like this

```yaml
# kubernetes-manifest.yaml
apiVersion: v1
kind: Pod
metadata:
  name: motoscrape
  namespace: prometheus
  labels:
    app.kubernetes.io: motoscrape
spec:
  containers:
  - name: modem-scrape
    image: smokes2345/motoscraper:latest
    ports:
    - containerPort: 8000
      name: metrics
    command: ["python", "scrape_modem.py", "http://192.168.100.1/MotoConnection.asp"]
```
