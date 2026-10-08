# Звіт: лабораторна робота №3

## Середовище

- Застосунок: Flask `orders`, порт 8001.
- Образи: `devopslab/orders:1.0.0` та `devopslab/orders:1.1.0`.
- Кластер: Minikube з Docker driver.
- Namespace: `devopslab`.

## Розгортання

Після `minikube start --driver=docker` і ввімкнення `metrics-server` та `ingress`
обидва образи зібрано й додано командою `minikube image load`. Маніфести
застосовуються однією командою з каталогу `k8s/`:

```powershell
kubectl apply -f .
kubectl get pods,deployments,replicasets,services -n devopslab
kubectl get pods -n devopslab -o wide
```

Стан застосунку та конфігурація:

```powershell
kubectl rollout status deployment/orders -n devopslab
kubectl exec -n devopslab deployment/orders -- printenv APP_ENV LOG_LEVEL ORDERS_REGION
kubectl exec -n devopslab deployment/orders -- printenv ORDERS_API_TOKEN
minikube service ingress-nginx-controller -n ingress-nginx --url
```

Токен у маніфесті — лише несправжнє демонстраційне значення. Не вставляйте у
звіт вивід справжніх секретів.

## Самовідновлення, масштабування та оновлення

```powershell
kubectl delete pod <ім'я-пода> -n devopslab
kubectl get pods -n devopslab -w
kubectl scale deployment/orders --replicas=4 -n devopslab
kubectl get pods -n devopslab -o wide
kubectl set image deployment/orders orders=devopslab/orders:1.1.0 -n devopslab
kubectl rollout status deployment/orders -n devopslab
kubectl rollout history deployment/orders -n devopslab
Invoke-RestMethod "$url/version"
kubectl rollout undo deployment/orders -n devopslab
kubectl rollout status deployment/orders -n devopslab
```

Під час rollout паралельно опитуйте `/health` через URL Ingress, щоб зберегти
доказ доступності. Розподіл запитів між репліками видно за відповідями
`/instance`.

## Діагностика

```powershell
kubectl set image deployment/orders orders=devopslab/orders:9.9.9 -n devopslab
kubectl get pods -n devopslab -w
kubectl describe pod <ім'я-пода> -n devopslab
kubectl get events -n devopslab --sort-by=.lastTimestamp
kubectl logs deployment/orders -n devopslab
kubectl exec -it deployment/orders -n devopslab -- /bin/sh
kubectl set image deployment/orders orders=devopslab/orders:1.0.0 -n devopslab
kubectl rollout status deployment/orders -n devopslab
```

## Фактичні результати

Перевірено на локальному кластері Minikube `v1.39.0`, Kubernetes `v1.37.0`,
Docker driver, 08.10.2026. Команда `kubectl apply -f .` із каталогу `k8s/`
застосувала всі шість ресурсів. Вузол `minikube` має `Ready`; системні поди та metrics-server
працюють, ingress-nginx controller має `1/1 Running`.

Після застосування:

```text
deployment.apps/orders   2/2 READY   image devopslab/orders:1.0.0
service/orders           NodePort    8001:30081/TCP
ingress/orders           nginx       ADDRESS 192.168.49.2
GET /health              {"service":"orders","status":"ok"}
GET /version             {"version":"1.0.0"}
GET /config              {"app_env":"production","log_level":"INFO","orders_region":"eu-central"}
ConfigMap env            production / INFO / eu-central
Secret env               ORDERS_API_TOKEN=set
```

HTTP URL через тунель до ingress controller: `http://127.0.0.1:51311`; його
`/health` також відкрито у браузері. Токен не виводився у звіт.

Після видалення `orders-747f6467f-8d7vm` Deployment автоматично створив
`orders-747f6467f-tdd9n`. Після масштабування до чотирьох реплік 30 запитів
до `/instance` розподілилися між усіма чотирма Pod-ами: 4, 13, 2 та 11 запитів.
Після демонстрації масштаб повернуто до двох реплік.

Rolling update через Ingress перевірено повторними HTTP-запитами:

```text
Після rollout до 1.1.0: /version = 1.1.0
Після kubectl rollout undo: /version = 1.0.0
Під час оновлення й відкату: 213 успішних /health перевірок, 0 помилок
```

`kubectl rollout history deployment/orders -n devopslab` показав кілька
ревізій, зокрема 7, 9, 10, 12, 14 та 15.

Для діагностики встановлено тег
`devopslab/orders:9.9.9-not-existing-lab3`. Pod `orders-69f5885c5d-5zbmc`
перейшов у `ImagePullBackOff`; `describe pod` та Events повідомили, що registry
не має такого образу (`pull access denied`, `repository does not exist or may
require authorization`). `kubectl logs` показав запуск Gunicorn 23.0.0 на
`0.0.0.0:8001`. Після повернення `devopslab/orders:1.0.0` Deployment відновив
стан `2/2 Ready`, `/health` повертає `status: ok`.

Shell-контейнера перевірено через stdin-сеанс:

```text
shell-entered
uid=10001 gid=10001 groups=10001
production
```

Для TTY у звичайному терміналі використовуйте команду `kubectl exec -it
deployment/orders -n devopslab -- /bin/sh` з розділу «Діагностика». Термінал
інструментального середовища не надає TTY, тому інтерактивний shell тут
перевірено через `kubectl exec -i`.

Фінальна перевірка: 5 тестів проходять, `ruff check services/orders`
повертає `All checks passed!`, а `kubectl apply --dry-run=server -f .\k8s\`
успішно перевірив усі маніфести.
