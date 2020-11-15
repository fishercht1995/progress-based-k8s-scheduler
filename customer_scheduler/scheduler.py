from __future__ import division
import time
import random
import json
import sys
import pandas as pd

from kubernetes import client, config, watch

config.load_incluster_config()
v1 = client.CoreV1Api()

scheduler_name = "my-scheduler"
import logging
#log = open("/data/scheduler.log","a")
job_result = open("/data/job_result.log","w")
job_result.write("job,end_time\n")
#logging.basicConfig(filename="/data/scheduler.log", filemode="a", format="%(asctime)s:%(message)s",level=logging.DEBUG)



def nodes_available():
    ready_nodes = []

    for n in v1.list_node().items:
        ready_nodes.append(n.metadata.name)
        for status in n.status.conditions:
            if status.type == 'Ready':
                if status.status == "False":
                    log.write("Reason:"+status.type + "\n")
                    ready_nodes.remove(n.metadata.name)
                    #logging.warning(n.metadata.name+" is not available")
                    break
            else:
                if status.status == "True":
                    #log.write("Reason:" + status.type + "\n")
                    ready_nodes.remove(n.metadata.name)
                    break
    for node in ready_nodes:
        if "master" in node:
            ready_nodes.remove(node)
    return ready_nodes

def get_total_iteration(pod_name):
    pods_list = v1.list_namespaced_pod(namespace="default").items
    for pod in pods_list:
        if pod.metadata.name == pod_name:
            return int(pod.spec.containers[0].args[1])
    return None

def scheduler(name, node, namespace='default'):
    """
    Bind a pod to a node
    :param name: pod name
    :param node: node name
    :param namespace: kubernetes namespace
    :return:
    """

    target = client.V1ObjectReference(kind = 'Node', api_version = 'v1', name = node)
    meta = client.V1ObjectMeta(name = name)
    body = client.V1Binding(target = target, metadata = meta)
    try:
        client.CoreV1Api().create_namespaced_binding(namespace=namespace, body=body)
    except ValueError:
        # PRINT SOMETHING or PASS
        pass

def read_report(node):
    """
    Get report from assistant pods
    :param node: node names
    :return: report's inforamtion: status,C,nums
    """

    report = pd.read_csv("/data/" + node + ".csv")
    last = report.shape[0]-1
    status = report.loc[last,"status"]
    C = float(report.loc[last,"C"])
    nums = int(report.loc[last,"numsofjobs"])
    pod_info = report.loc[last,"P_info"]
    return status,C,nums,pod_info


def get_job_info(pod_name):
    try:
        info = pd.read_csv("/data/" + pod_name + ".csv")
        last = info.shape[0]-1
        if last == 0:
            total_iteration = get_total_iteration(pod_name)
            return (total_iteration,-1,0)
        total_iteration = int(info.loc[last,"total_iteration"])
        current_iteration = int(info.loc[last,"num_iteration"])
        iteration_time = float(info.loc[last,"epoch_time"])
        return (total_iteration,current_iteration,iteration_time)
    except Exception as e:
        #log.write(str(e))
        total_iteration = get_total_iteration(pod_name)
        return (total_iteration, -1, 0)


def cal_EC(pods,U,pod_submit):
    P = {}
    max_P = 0
    sys_time = float(time.time())
    for pod in pods:
        total_iteration,current_iteration,iteration_time = get_job_info(pod)
        if current_iteration != -1:
            P[pod] = (iteration_time*U)*(total_iteration-current_iteration)
            #log.write("iteration_time:{}\ttotal_iteration:{}\tcurrent_iteration:{}\n".format(str(iteration_time),
                                                                                             str(total_iteration),
                                                                                             str(current_iteration)))
        else:
            P[pod] = ((sys_time-pod_submit[pod])*U)*total_iteration
            #log.write("sys_time:{}\tpod_submit:{}\ttotal_iteration:{}\n".format(str(sys_time),
                                                                                str(pod_submit[pod]),
                                                                                str(total_iteration)))
        if P[pod] > max_P:
            max_P = P[pod]
        #log.write("pod:{},P:{}\n".format(pod,str(P[pod])))
    #log.write("\n")
    EJR = {}
    for i in range(int(max_P+1)):
        EJR[i] = 0
        for pod in P:
            if P[pod] > i:
               EJR[i] += 1

    C = 1
    for t in EJR:
        C += EJR[t]
    #logging.warning("Node:{}\tC:{}".format(node,C))
    return C



def algorithm_2(nodes,nodes_pods_dict,pod_submit):
    """
    Implement algorithm 2 in the paper
    :param nodes: avaliable nodes
    :param nodes_pods_dict: current node-pod pair
    :return: best node
    """

    CS = {}
    #logging.warning("Algorithm_2 running")
    for node in nodes:
        node_report = read_report(node)
        nodes_pods_nums = len(nodes_pods_dict[node])

        new_C = node_report[1]*nodes_pods_nums
        node_report = node_report[0],new_C,nodes_pods_nums,node_report[3]
        #logging.warning("In node:{}\tstatus:{}\tC:{}\tjobs number:{}".format(node, node_report[0],
        #                                                                     str(node_report[1]),
        #                                                                     str(nodes_pods_nums)))
        #log.write("In node:{}\nstatus:{}\tC:{}\tjobs number:{}\n".format(node, node_report[0],
                                                                             str(node_report[1]),
                                                                            str(nodes_pods_nums)))
        #log.write("P_info:\n{}\n".format(node_report[3]))
        #log.flush()
        if node_report[0] != "outoflimit":
            CS[node] = node_report
    if len(CS.keys()) > 0:
        #logging.warning("since |CS|>0, sort CS")
        #log.write("since |CS|>0, sort CS\n")
        #choose the node with miniminal C
        sorted_CS = sorted(CS.items(),key=lambda x: x[1][1])
        for item in sorted_CS:
            #log.write("node:{}\tC:{}\n".format(item[0], str(item[1][1])))
            #log.flush()
            #logging.warning("node:{}\tC:{}".format(item[0],str(item[1][1])))
        return sorted_CS[0][0]
    else:
        try:
            #logging.warning("since |CS| == 0, recalculate EC")
            #log.write("since |CS| == 0, recalculate EC\n")
            #recalculate EC
            EC = {}
            for node in nodes_pods_dict:
                U = (len(nodes_pods_dict[node]))
                #log.write("U:{}\n".format(str(U)))
                #log.write("node:{}\n".format(node))
                EC[node] = cal_EC(nodes_pods_dict[node],U,pod_submit)
                EC[node] *= len(nodes_pods_dict[node])
                #log.write("node:{}\tEC:{}\n".format(node,str(EC[node])))
            sorted_ES = sorted(EC.items(),key = lambda x:x[1])
            for item in sorted_ES:
                #log.write("node:{}\tEC:{}\n".format(item[0],str(item[1])))
                #log.flush()
                pass
            #logging.warning("node:{}\tEC:{}".format(item[0],str(item[1])))
            return sorted_ES[0][0]
        except Exception as e:
            #log.write(str(e))
            #log.flush()

def check_pod(target_pod):
    pod = v1.read_namespaced_pod(namespace="default", name=target_pod)
    if pod.status.phase == "Succeeded":
        #log.write("pod{} terminated because of Completed\n".format(target_pod))
        job_result.write("{},{}\n".format(target_pod,str(time.time())))
        job_result.flush()
        log.flush()
        #logging.warning("pod{} terminated because of Completed".format(target_pod))
        return True
    else:
        return False


def update_working_pods(nodes_pods_dict):
    for node in nodes_pods_dict:
        for pod in nodes_pods_dict[node]:
            completed = check_pod(pod)
            if completed:
                nodes_pods_dict[node].remove(pod)
    return nodes_pods_dict



def main():
    # creat node log
    nodes_pods_dict = {}
    nodes = nodes_available()
    for node in nodes:
        nodes_pods_dict[node] = []
        f = open("/data/" + node + ".log", "a")
        f.write("job,time\n")
        f.close()
    w = watch.Watch()
    #Create pod submitted time dict
    pod_submit = {}
    pod_name = ""
    for event in w.stream(v1.list_namespaced_pod, "default"):
        nodes_pods_dict = update_working_pods(nodes_pods_dict)
        if event['object'].status.phase == "Pending" and event['object'].spec.scheduler_name == scheduler_name:
            new_pod_name = event['object'].metadata.name
            if pod_name == new_pod_name:
                continue
            pod_name = new_pod_name
            #log.write("{}:{} need to be scheduled\n".format(str(time.time()),pod_name))
            #log.flush()
            try:
                pod_submit[event['object'].metadata.name] = float(time.time())
                nodes = nodes_available()
                #log.write("There are "+str(len(nodes))+" nodes available\n")
                #log.flush()
                #logging.warning("There are "+str(len(nodes))+" nodes available")
                while True:
                    nodes = nodes_available()
                    node = algorithm_2(nodes,nodes_pods_dict,pod_submit)
                    if node in nodes_available():
                        break
                nodes_pods_dict[node].append(event['object'].metadata.name)
                f = open("/data/" + node + ".log", "a")
                f.write(str(event['object'].metadata.name) + ","+str(float(time.time()))+"\n")
                f.flush()
                f.close()
                #log.write("Implement job:{} to node:{}\n".format(event['object'].metadata.name, node))
                #log.flush()
                res = scheduler(event['object'].metadata.name, node)
                #logging.warning("Implement job:{} to node:{}".format(event['object'].metadata.name,node))
                print event['object'].metadata.name+" has been locate to "+node
            except client.rest.ApiException as e:
                print json.loads(e.body)['message']
    #log.close()


if __name__ == '__main__':
    main()
