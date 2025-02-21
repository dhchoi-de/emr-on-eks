#!/bin/bash

CLUSTER_NAME=$CLUSTER_NAME
NAMESPACE=$NAMESPACE
SERVICE_ACCOUNT=$SERVICE_ACCOUNT
EMR_JOB_EXECUTION_ROLE_NAME=$EMR_JOB_EXECUTION_ROLE_NAME
VIRTUAL_CLUSTER_NAME=$VIRTUAL_CLUSTER_NAME

# IAM Identity Mapping 설정
eksctl create iamidentitymapping \
    --cluster $CLUSTER_NAME \
    --namespace $NAMESPACE \
    --service-name $SERVICE_ACCOUNT_NAME

# EKS 클러스터에 IAM OIDC Provider 연결
eksctl utils associate-iam-oidc-provider \
    --cluster $CLUSTER_NAME --approve

# EMR 작업 실행을 위한 IAM 역할을 생성하고 신뢰 정책을 설정
aws iam create-role \
  --role-name $EMR_JOB_EXECUTION_ROLE_NAME \
  --assume-role-policy-document file://../json/emr-trust-policy.json

# EMR 컨테이너 작업 실행을 위한 IAM 역할에 정책을 추가
aws iam put-role-policy \
  --role-name $EMR_JOB_EXECUTION_ROLE_NAME \
  --policy-name EMR-Containers-Job-Execution \
  --policy-document file://../json/EMRContainers-JobExecutionRole.json

# EMR Job이 특정 IAM 역할을 사용할 수 잇도록 신뢰 정책 업데이트
aws emr-containers update-role-trust-policy \
  --cluster-name $CLUSTER_NAME \
  --namespace $NAMESPACE \
  --role-name $EMR_JOB_EXECUTION_ROLE_NAME

# EMR에서 EKS 클러스터를 가상 클러스터로 등록하여 EMR이 Kubernetes 클러스터에서 작업을 실행할 수 있도록 설정
aws emr-containers create-virtual-cluster \
  --name $VIRTUAL_CLUSTER_NAME \
  --container-provider '{
        "id": "$CLUSTER_NAME",
        "type": "EKS",
        "info": {
            "eksInfo": {
                "namespace": "$NAMESPACE"
            }
        }
    }'
