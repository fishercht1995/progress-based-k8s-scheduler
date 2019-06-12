# Deploy prometheus + grafana for k8s

## Prerequisite
We need a ready and all running k8s cluster (referring to Deploy_k8s_cluster.md)

# On master 
```
git clone https://github.com/redhatxl/k8s-prometheus-grafana.git
```

# On slaves
```
docker pull prom/node-exporter
docker pull prom/prometheus:v2.0.0
docker pull grafana/grafana:4.2.0
``

# On master
```
kubectl create -f  k8s-prometheus-grafana/node-exporter.yaml 
kubectl create -f  k8s-prometheus-grafana/prometheus/rbac-setup.yaml
kubectl create -f  k8s-prometheus-grafana/prometheus/configmap.yaml 
kubectl create -f  k8s-prometheus-grafana/prometheus/prometheus.deploy.yml 
kubectl create -f  k8s-prometheus-grafana/prometheus/prometheus.svc.yml 
kubectl create -f   k8s-prometheus-grafana/grafana/grafana-deploy.yaml
kubectl create -f   k8s-prometheus-grafana/grafana/grafana-svc.yaml
kubectl create -f   k8s-prometheus-grafana/grafana/grafana-ing.yaml


