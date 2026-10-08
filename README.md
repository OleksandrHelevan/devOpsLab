# DevOps Lab: мікросервіс orders

Репозиторій містить Flask-сервіси `users` і `orders`. У лабораторній роботі №3
в Kubernetes розгортається `orders` (`services/orders`), який слухає порт 8001.

## Локальні перевірки та збірка

Потрібні Python 3.12, Docker Desktop із запущеним Docker Engine, Minikube та
сумісний `kubectl`. У Windows встановіть інструменти через WinGet:

```powershell
winget install --id Kubernetes.minikube --exact
winget install --id Kubernetes.kubectl --exact --version 1.37.1
```

Для Minikube v1.39.0 нижче зафіксовано Kubernetes v1.37.0; використовуйте
`kubectl` тієї самої або сусідньої minor версії (`kubectl version --client`).
Запускайте команди з PowerShell.

```powershell
py -m pip install -r services/orders/requirements-dev.txt
py -m ruff check services/orders
py -m pytest services/orders
docker build --build-arg APP_VERSION=1.0.0 -t devopslab/orders:1.0.0 services/orders
docker build --build-arg APP_VERSION=1.1.0 -t devopslab/orders:1.1.0 services/orders
```

Обидва образи навмисно мають незмінні теги версій; `latest` не використовується.
Для приватного registry завантажте ці два теги туди та замініть `image` у
`k8s/30-deployment.yaml` на повне ім'я образу.

## Розгортання з нуля у Minikube

Запустіть Docker Desktop, встановіть Minikube та `kubectl`, потім із PowerShell:

```powershell
minikube start --driver=docker --kubernetes-version=v1.37.0
kubectl get nodes
kubectl get pods -n kube-system
minikube addons enable metrics-server
minikube addons enable ingress
minikube image load devopslab/orders:1.0.0
minikube image load devopslab/orders:1.1.0
Set-Location .\k8s
kubectl apply -f .
kubectl rollout status deployment/orders -n devopslab
kubectl get pods,deployments,replicasets,services -n devopslab
```

Кожен об'єкт має власний YAML у `k8s/`; номери файлів забезпечують створення
namespace, ConfigMap і Secret перед Deployment, Service та Ingress. Service
має тип NodePort, а Ingress маршрутизує HTTP-запити до `orders`. Для доступу з
хоста відкрийте стабільний тунель до Ingress Controller:

```powershell
minikube service ingress-nginx-controller -n ingress-nginx --url
```

Команда друкує URL; відкрийте його з `/health`, `/orders`, `/config` або
`/version` у браузері. У разі Docker driver на Windows залиште команду
`minikube service` запущеною, поки перевіряєте URL. Тунель до Ingress
Controller не змінюється, коли Deployment замінює application Pods під час
rollout.

### Параметри конфігурації

`orders-config` (`k8s/10-configmap.yaml`) передає контейнеру:

| Змінна | Значення для лабораторної | Призначення |
| --- | --- | --- |
| `APP_ENV` | `production` | Режим застосунку |
| `LOG_LEVEL` | `INFO` | Рівень журналювання |
| `ORDERS_REGION` | `eu-central` | Регіон сервісу |

`orders-secret` (`k8s/20-secret.yaml`) містить `ORDERS_API_TOKEN` з явним
демонстраційним значенням, яке не є обліковими даними. Secret Kubernetes
кодується, але сам по собі не шифрується; не додавайте до маніфесту реальні
паролі/ключі. У робочому середовищі передавайте значення через захищене сховище.
`/config` повертає лише не секретні поля. Перевірити отримання змінних у
контейнері можна так:

```powershell
kubectl exec -n devopslab deployment/orders -- printenv APP_ENV LOG_LEVEL ORDERS_REGION
kubectl exec -n devopslab deployment/orders -- printenv ORDERS_API_TOKEN
```

Другу команду виконуйте лише для демонстраційного токена; не зберігайте її
вивід із реальними секретами у звітах.

## Керування життєвим циклом

### Самовідновлення та масштабування

```powershell
kubectl get pods -n devopslab -o wide
$pod = kubectl get pods -n devopslab -o jsonpath='{.items[0].metadata.name}'
kubectl delete pod $pod -n devopslab
kubectl get pods -n devopslab -w
kubectl scale deployment/orders --replicas=4 -n devopslab
kubectl get pods -n devopslab -o wide
```

Для перевірки розподілу запитів скопіюйте URL Ingress, отриманий через
`minikube service`, у змінну `$url` та опитайте `/instance` кілька разів:

```powershell
$url = "http://127.0.0.1:<порт>"
1..20 | ForEach-Object { (Invoke-RestMethod "$url/instance").instance } | Group-Object
```

### Rolling update, історія та відкат

Після попереднього завантаження тегів у Minikube оновіть образ:

```powershell
kubectl set image deployment/orders orders=devopslab/orders:1.1.0 -n devopslab
kubectl rollout status deployment/orders -n devopslab
kubectl rollout history deployment/orders -n devopslab
kubectl get pods -n devopslab -w
Invoke-RestMethod "$url/version"
kubectl rollout undo deployment/orders -n devopslab
kubectl rollout status deployment/orders -n devopslab
Invoke-RestMethod "$url/version"
```

Під час оновлення `maxUnavailable: 0` зберігає доступні репліки, доки нова
репліка не стане Ready. Щоб зафіксувати доступність, запустіть повторні запити
до `$url/health` у другому вікні PowerShell одночасно з `rollout status`.

## Діагностика

Навмисно задайте відсутній тег, перегляньте стан і причину, а потім відновіть
робочу версію:

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

Значення `<ім'я-пода>` візьміть із `kubectl get pods`. Після виправлення
переконайтеся, що обидві репліки Ready та `/health` повертає `status: ok`.

## Звіт

Короткий порядок виконання та команди для збереження фактичного виводу
розташовані в [k8s/lab3-report.md](./k8s/lab3-report.md). Додайте туди власні
скриншоти або результати команд після запуску кластера.
