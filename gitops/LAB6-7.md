# ЛР6–7: порядок запуску й демонстрації

Застосунок `orders`, namespace `orders`, Service `orders:8001`, порти: Argo CD 8080, Grafana 3000.

## 0. Підготовка (Docker Desktop має бути запущений)
```powershell
minikube delete; minikube start --cpus 4 --memory 8192
kubectl create namespace argocd
kubectl apply -n argocd --server-side --force-conflicts -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl create namespace orders;     # + orders-secret з ЛР5
kubectl create namespace monitoring
kubectl -n monitoring create secret generic grafana-admin --from-literal=admin-user=admin --from-literal=admin-password=<пароль>
# образи (метрики є лише з нової версії коду); тег 1.1.0 теж треба перебілдити
foreach ($v in "1.1.0","1.2.0","1.3.0") { docker build --build-arg APP_VERSION=$v -t devopslab/orders:$v services/orders; minikube image load devopslab/orders:$v }
```
## 1. Порядок комітів (кожен — дочекатися Healthy)
1. `argocd-apps/argo-rollouts.yaml`
2. `argocd-apps/kps.yaml`, `loki.yaml`, `alloy.yaml`
3. чарт `orders` 0.3.0 (Rollout, ServiceMonitor, дашборд, AnalysisTemplate) + оновлений `orders.yaml`
```powershell
kubectl apply -f gitops/bootstrap/root.yaml
```
## 2. ЛР6: canary / blue-green
- canary — `values-minikube.yaml` (кроки: 20% → пауза → аналіз → 60% → пауза).
  Для ручної паузи з ЛР6 замініть першу `pause: {duration: 30s}` на `pause: {}` і приберіть `analysis`.
- blue-green — додайте `values-minikube-bluegreen.yaml` у `valueFiles` Application.
- Реліз: змінити `image.tag` на `1.2.0`, push. `kubectl argo rollouts get rollout orders -n orders --watch`,
  `kubectl argo rollouts promote|abort orders -n orders`.
## 3. ЛР7: метрики, логи, відкат
```powershell
kubectl -n monitoring port-forward svc/kps-grafana 3000:80
kubectl -n monitoring port-forward svc/kps-prometheus 9090:9090
kubectl create deployment load --image=curlimages/curl -- sh -c 'while true; do curl -s -o /dev/null http://orders.orders.svc:8001/orders; sleep 0.05; done'
```
Поганий реліз: у `values-minikube.yaml` `FAIL_RATE: "0.5"` (і новий тег), push → AnalysisRun Failed →
`kubectl -n orders get analysisrun`, `describe analysisrun <name>` → `git revert <коміт> && git push`.
Для blue-green додатково: `kubectl create deployment load-preview ... http://orders-preview.orders.svc:8001/orders`.

PromQL/LogQL: `sum by (status) (rate(http_requests_total{namespace="orders"}[1m]))`,
`{namespace="orders"} | json | status >= 500`.
