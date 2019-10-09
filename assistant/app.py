from __future__ import print_function,division

import time
import random
import json
import pandas as pd
import sys
import os
import psutil

from kubernetes import client, config, watch

config.load_incluster_config()
v1 = client.CoreV1Api()
node_name,alpha,total = sys.argv[1:]

import logging

log = open("/data/"+node_name+"-track.log","w")
#logging.basicConfig(filename="/data/"+node_name+"-track.log", filemode="w", format="%(asctime)s:%(message)s",level=logging.DEBUG)

#logging.basicConfig(filename="a.csv", filemode="w", format="%(message)s",level=logging.DEBUG)
def get_pods(node_name):
    """
    Getting all pods bining to this nodes through scheduler log. The log may include completed jobs.
    Completed jobs can be deleted through implementing algorithm 1
    :param node_name: node name
    :return: list[pods]
    """

    file_name = "/data/"+node_name+".log"
    while os.path.exists(file_name) == False:
        time.sleep(1)
    data = pd.read_csv(file_name)
    dic = {}
    for i in range(data.shape[0]):
        dic[data.loc[i,"job"]] = float(data.loc[i,"time"])
    return dic

def get_total_iteration(pod_name):
    pods_list = v1.list_namespaced_pod(namespace="default").items
    for pod in pods_list:
        if pod.metadata.name == pod_name:
            return int(pod.spec.containers[0].args[1])

def get_pod_info(pod_name):
    """
    Generate information from logs printed by jobs
    :param pod_name: pod name
    :return: information include (pod_name,cpu,total_iteration,current_iteration,iteration_time)
    """

    try:
        info = pd.read_csv("/data/" + pod_name + ".csv")
        last = info.shape[0]-1
        if last != 0:
            cpu = float(info.loc[last,"cpu"])
            total_iteration = int(info.loc[last,"total_iteration"])
            current_iteration = int(info.loc[last,"num_iteration"])
            iteration_time = float(info.loc[last,"epoch_time"])
            return (pod_name,cpu,total_iteration,current_iteration,iteration_time)
        else:
            total_iteration = get_total_iteration(pod_name)
            return (pod_name, 0, total_iteration, -1, 0)
    except :
        while True:
            total_iteration = get_total_iteration(pod_name)
            if total_iteration != None:
                return (pod_name,0,total_iteration, -1, 0)

def check_pod(target_pod):
    pod = v1.read_namespaced_pod(namespace="default",name = target_pod)
    if pod.status.phase == "Succeeded":
        return False
    else:
        return True
def algorithm_1(node_name,alpha,total):
    """
    Implement algorithm 1 in the paper
    :param node_name: node_name
    :param alpha: rate for up-boundary
    :param total: total available cpu for node
    :return: status,C,used_cpu
    """

    log.write("Algorithm_1 running\n")
    pods_dic = get_pods(node_name)
    pods = list(pods_dic.keys())
    pods = filter(lambda pod:check_pod(pod),pods)
    working_jobs = len(pods)
    log.write("get working pods info {}, number:{}\n".format(str(pods),str(working_jobs)))
    log.flush()
    #collect info of pods
    #using a additional P to handle no inforamtion gain from jobs logs
    dic = {}
    P = {}
    additional_P  = {}
    for pod in pods:
        info = get_pod_info(pod)
        log.write("pod:{},info:{}\n".format(pod,str(info)))
        if info[3] != -1:
            dic[info[0]] = info[1:]
        else:
            total_iteration = info[2]
            start_time = pods_dic[pod]
            additional_P[pod] = (total_iteration,start_time)
            log.write("pod:{}info:{}\n".format(pod,str(additional_P[pod])))
    #if used_cpu < alpha * total, return false
    used_cpu = 0
    for pod in dic:
        if dic[pod][1] > dic[pod][2]:
            used_cpu += dic[pod][0]
    try:
        used_cpu = (working_jobs/len(dic.keys()))*used_cpu
    except :
        used_cpu = 0
    used_cpu = total if used_cpu > total else used_cpu
    if used_cpu > alpha * total:
        log.write("Terminating algorithm beacuse:\tPods out of alpha limit with total cpu:{}. Return default value\n".format(str(used_cpu)))
        return "outoflimit",-1,working_jobs,used_cpu,P
    #generate P for each pod
    max_pj = 0
    #Getting P in normal
    log.write("There are {} working jobs\n".format(str(working_jobs)))
    nums_of_jobs = working_jobs
    for pod in dic:
        try:
            Uj = dic[pod][0]/used_cpu
            Pj = (dic[pod][3]/Uj)*(dic[pod][1]-dic[pod][2])
            log.write("pod:{}\tU:{}\tP:{}\n".format(pod,str(Uj),str(Pj)))
            if Pj > max_pj:
                max_pj = Pj
            P[pod] = Pj
        except ZeroDivisionError:
            log.write("pod:{},zeroDivisionError\n".format(pod))
    log.write("Normal P:{}\n".format(str(P)))
    #Getting P in additional
    sys_time = float(time.time())
    log.write("additional_P:{}.nums:{}\n".format(str(additional_P),str(nums_of_jobs)))
    log.flush()
    for pod in additional_P:
        try:
            Ua = 1/nums_of_jobs
            Pa = ((sys_time-additional_P[pod][1])/Ua)*additional_P[pod][0]
            log.write("pod:{}\tU:{}\tAdditiona_P:{}\n".format(pod,str(Ua),str(Pa)))
            if Pa > max_pj:
                max_pj = Pa
            P[pod] = Pa
        except ZeroDivisionError:
            log.write("pod:{},nums:{}zeroDivisionError\n".format(pod,str(nums_of_jobs)))
    log.write("Total P:{}\n".format(str(P)))
    #generate EJR
    EJR = {}
    max_pj = int(max_pj)
    for i in range(max_pj+1):
        EJR[i] = 0
        for pod in P:
            if P[pod] > i:
               EJR[i] += 1
    #calculate rank values
    C = 1
    for t in EJR:
        C += EJR[t]
    log.write("C:{}\tstatus:{}\tused_cpu:{}\n".format(str(C),"ready",str(used_cpu)))
    log.write("Algorithm 1 finished.\n")
    log.flush()
    return "ready",C,working_jobs,used_cpu,P

def report(cur_time,node_name,status,C,nums,used_cpu,P):
    """
    Generate report sent to scheduler
    :param cur_time: current system time
    :param node_name: node name
    :param status:
    :param C:
    :param nums:
    :param used_cpu:
    :return:
    """
    p_info = ""
    for pod in P:
        p_info += pod+":"+str(P[pod])+"\t"
    f = open("/data/"+node_name+".csv","a")
    f.write("{},{},{},{},{},{}\n".format(cur_time,status,str(C),nums,used_cpu,p_info))
    f.close()


def main():
    f = open("/data/" + node_name + ".csv", "w")
    f.write("cur_time,status,C,numsofjobs,used_cpu,P_info\n")
    f.close()
    while True:
    #w = watch.Watch()
    #for event in w.stream(v1.list_namespaced_pod, "default"):
        #if event['object'].status.phase == "Pending":
            #new_pod = event['object'].metadata.name
        status,C,nums,used_cpu,P = algorithm_1(node_name,float(alpha),float(total))
        cur_time = time.time()
        report(cur_time,node_name,status,C,nums,used_cpu,P)
        time.sleep(0.5)

if __name__ == "__main__":
    main()