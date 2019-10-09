# cloudinstall
install files

### kubernetes
### prometheus + grafana for k8s
### nfs system

### Useful Links:


https://github.com/kubernetes-client/python/blob/master/kubernetes/docs/CoreV1Api.md


https://docs.docker.com/get-started/ 


https://kubernetes.io/docs/home/



### k8s control


apply/create/get/delete/describe/logs/


pod/node/pv/pvc/service/deployment/namespace/


role based assess control(RBAC)

### Advanced command

kubectl get pod -o=custom-columns=NODE:.spec.nodeName,NAME:.metadata.name


### Client Api

When your program lanch kubernetes system config, the code is slightly different in pod and master local environment. 

In pod:
```
config.load_incluster_config()
v1 = client.CoreV1Api()
```
