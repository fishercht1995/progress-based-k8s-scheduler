# Deploy k8s cluster

1. First install docker and k8s on both master and slaves nodes:
```
apt-get update -y
swapoff -a

apt-get update && apt-get install apt-transport-https ca-certificates curl software-properties-common

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
add-apt-repository \
  "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) \
  stable"

apt-get update && apt-get install docker-ce=18.06.2~ce~3-0~ubuntu

cat > /etc/docker/daemon.json <<EOF
{
  "exec-opts": ["native.cgroupdriver=systemd"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m"
  },
  "storage-driver": "overlay2"
}
EOF

mkdir -p /etc/systemd/system/docker.service.d

systemctl daemon-reload
systemctl restart docker

apt-get update && apt-get install -y apt-transport-https curl

curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -

cat << EOF >/etc/apt/sources.list.d/kubernetes.list
deb https://apt.kubernetes.io/ kubernetes-xenial main
EOF

apt-get update
apt-get install -y kubelet kubeadm kubectl
apt-mark hold kubelet kubeadm kubectl
```

2. Only on master node:
```
kubeadm init --pod-network-cidr=10.244.0.0/16

mkdir -p $HOME/.kube
cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
chown $(id -u):$(id -g) $HOME/.kube/config

kubectl apply -f "https://cloud.weave.works/k8s/net?k8s-version=$(kubectl version | base64 | tr -d '\n')"

kubectl taint nodes --all node-role.kubernetes.io/master-

kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml
```

3. On each slaves nodes copy and run what you got in kubeadm init: (example)
````
kubeadm join 128.110.153.78:6443 --token 7cmbqs.zx7j57hzp64zwcei \
    --discovery-token-ca-cert-hash sha256:ac04125e58767ddf33e390848a7b9beac0e79b537393998b0349296e72cc6bc6
```

4. check status on master node:
```
kubectl get nodes
kubectl get pod --all-namespaces
```
# all nodes should be ready: (example)

NAME                                               STATUS   ROLES    AGE     VERSION
cp-1.zsl3203-qv50305.shield-pg0.wisc.cloudlab.us   Ready    <none>   99s     v1.14.1
cp-2.zsl3203-qv50305.shield-pg0.wisc.cloudlab.us   Ready    <none>   97s     v1.14.1
ctl.zsl3203-qv50305.shield-pg0.wisc.cloudlab.us    Ready    master   3m49s   v1.14.1







