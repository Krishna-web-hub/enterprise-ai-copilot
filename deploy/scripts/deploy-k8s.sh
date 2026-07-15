#!/bin/bash
# ============================================================
# Kubernetes Deployment Script
# ============================================================
# Deploys the application to a Kubernetes cluster.
#
# Prerequisites:
# - kubectl configured with cluster access
# - Container images pushed to registry
# - k8s/secret.yml populated with real base64 values
#
# Usage:
#   ./deploy/scripts/deploy-k8s.sh [apply|delete|status|rollout]

set -euo pipefail

K8S_DIR="k8s"
NAMESPACE="ai-copilot"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log() { echo -e "${GREEN}[K8S]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

check_prerequisites() {
    command -v kubectl >/dev/null 2>&1 || error "kubectl is not installed"
    kubectl cluster-info >/dev/null 2>&1 || error "kubectl cannot reach the cluster"
}

apply() {
    check_prerequisites
    log "Applying Kubernetes manifests..."

    kubectl apply -f "$K8S_DIR/namespace.yml"
    kubectl apply -f "$K8S_DIR/configmap.yml"
    kubectl apply -f "$K8S_DIR/secret.yml"
    kubectl apply -f "$K8S_DIR/backend-deployment.yml"
    kubectl apply -f "$K8S_DIR/backend-service.yml"
    kubectl apply -f "$K8S_DIR/celery-deployment.yml"
    kubectl apply -f "$K8S_DIR/frontend-deployment.yml"
    kubectl apply -f "$K8S_DIR/hpa.yml"
    kubectl apply -f "$K8S_DIR/ingress.yml"

    log "All manifests applied. Waiting for rollout..."
    kubectl -n "$NAMESPACE" rollout status deployment/copilot-backend --timeout=120s
    kubectl -n "$NAMESPACE" rollout status deployment/copilot-frontend --timeout=60s

    log "Deployment complete!"
    status
}

delete() {
    log "Deleting all resources in namespace $NAMESPACE..."
    kubectl delete namespace "$NAMESPACE" --ignore-not-found
    log "Namespace deleted."
}

status() {
    log "Cluster status for namespace: $NAMESPACE"
    echo ""
    kubectl -n "$NAMESPACE" get pods -o wide
    echo ""
    kubectl -n "$NAMESPACE" get svc
    echo ""
    kubectl -n "$NAMESPACE" get hpa
    echo ""
    kubectl -n "$NAMESPACE" get ingress
}

rollout() {
    log "Triggering rolling restart of backend..."
    kubectl -n "$NAMESPACE" rollout restart deployment/copilot-backend
    kubectl -n "$NAMESPACE" rollout restart deployment/copilot-celery
    kubectl -n "$NAMESPACE" rollout status deployment/copilot-backend --timeout=120s
    log "Rollout complete."
}

case "${1:-apply}" in
    apply)   apply ;;
    delete)  delete ;;
    status)  status ;;
    rollout) rollout ;;
    *)       echo "Usage: $0 [apply|delete|status|rollout]"; exit 1 ;;
esac
