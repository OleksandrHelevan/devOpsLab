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

# Лабораторна №4: Helm-чарт `orders`

Маніфести з `k8s/` перенесено у власний чарт [helm/orders](./helm/orders):

```text
helm/orders/
├── Chart.yaml            # name, description, version, appVersion
├── values.yaml           # значення за замовчуванням (= dev)
├── values-dev.yaml       # середовище розробки
├── values-prod.yaml      # продакшн
├── .helmignore
└── templates/
    ├── _helpers.tpl          # orders.fullname, orders.labels, orders.selectorLabels, ...
    ├── configmap.yaml        # ← k8s/10-configmap.yaml
    ├── secret.yaml           # ← k8s/20-secret.yaml (значення з .Values.secret)
    ├── deployment.yaml       # ← k8s/30-deployment.yaml
    ├── service.yaml          # ← k8s/40-service.yaml
    ├── ingress.yaml          # ← k8s/50-ingress.yaml (ingress.enabled)
    ├── pvc.yaml              # необов'язковий PVC (persistence.enabled)
    ├── hook-pre-upgrade.yaml # хук pre-upgrade (завдання 9b)
    ├── NOTES.txt             # підказка після встановлення
    └── tests/test-connection.yaml  # тест релізу для helm test
```

`k8s/00-namespace.yaml` не перенесено в шаблон: namespace створює сам Helm
прапорцем `--create-namespace`, а всі об'єкти беруть namespace з
`.Release.Namespace`. Імена об'єктів будуються з імені релізу
(`orders-dev`, `orders-dev-config`, `orders-dev-secret`, ...), тому чарт можна
встановити двічі в один кластер (наприклад, `orders-dev` і `orders-prod`).
Фіксований `nodePort: 30081` з лабораторної №3 прибрано з дефолтів — інакше
другий реліз конфліктував би за порт; за потреби його задають
`--set service.nodePort=30081`.

### `version` і `appVersion`

| Поле | Значення | Що означає для цього проєкту |
| --- | --- | --- |
| `version` | `0.1.0` | Версія **чарта**: шаблонів, `values.yaml`, хуків. Збільшується (SemVer) при будь-якій зміні в `helm/orders/`, навіть якщо код `orders` не змінювався. Саме з цією версією чарт пакується (`orders-0.1.0.tgz`) і публікується в реєстр. |
| `appVersion` | `1.0.0` | Версія **застосунку** `services/orders` — тег Docker-образу `devopslab/orders`. Використовується як тег за замовчуванням, коли `image.tag` порожній, і потрапляє в мітку `app.kubernetes.io/version`. Змінюється, коли збирається новий образ (`1.1.0`). |

Тобто новий образ `1.1.0` без змін у шаблонах → `appVersion: 1.1.0`,
`version: 0.1.1`; нова можливість у чарті (наприклад PVC) при тому самому
образі → `version: 0.2.0`, `appVersion` без змін.

### Параметри values

| Параметр | За замовчуванням (dev) | prod | Опис |
| --- | --- | --- | --- |
| `replicaCount` | `1` | `3` | Кількість реплік Deployment |
| `revisionHistoryLimit` | `5` | `5` | Кількість збережених ReplicaSet |
| `image.repository` | `devopslab/orders` | — | Репозиторій образу |
| `image.tag` | `""` (= `appVersion` `1.0.0`) | `1.1.0` | Тег образу (dev-файл: `1.0.0`) |
| `image.pullPolicy` | `IfNotPresent` | — | Політика завантаження образу |
| `nameOverride` / `fullnameOverride` | `""` | — | Перевизначення імен об'єктів |
| `service.type` | `NodePort` | `ClusterIP` | Тип Service |
| `service.port` | `8001` | — | Порт Service |
| `service.nodePort` | `""` (авто) | — | Фіксований nodePort (лише для NodePort) |
| `containerPort` | `8001` | — | Порт контейнера |
| `resources.requests` | `cpu: 50m`, `memory: 64Mi` | `cpu: 100m`, `memory: 128Mi` | Запити ресурсів |
| `resources.limits` | `cpu: 250m`, `memory: 128Mi` | `cpu: 500m`, `memory: 256Mi` | Ліміти ресурсів |
| `config.appEnv` | `development` | `production` | `APP_ENV` у ConfigMap |
| `config.logLevel` | `DEBUG` | `INFO` | `LOG_LEVEL` у ConfigMap |
| `config.ordersRegion` | `local` | `eu-central` | `ORDERS_REGION` у ConfigMap |
| `secret.apiToken` | `""` | `""` (передається `--set`) | `ORDERS_API_TOKEN`; порожнє — згенерувати й зберігати між upgrade |
| `secret.existingSecret` | `""` | — | Використати вже створений Secret замість шаблону |
| `ingress.enabled` | `false` | `true` | Створювати Ingress |
| `ingress.className` | `nginx` | `nginx` | IngressClass |
| `ingress.host` | `""` | `""` | Хост правила (порожній — будь-який) |
| `ingress.path` / `ingress.pathType` | `/` / `Prefix` | — | Шлях маршрутизації |
| `ingress.annotations` | `{}` | — | Анотації Ingress |
| `persistence.enabled` | `false` | `false` | Створювати PVC і монтувати його |
| `persistence.size` | `1Gi` | — | Розмір PVC |
| `persistence.storageClass` | `""` | — | StorageClass (порожній — дефолтний) |
| `persistence.accessModes` | `[ReadWriteOnce]` | — | Режими доступу PVC |
| `persistence.mountPath` | `/data` | — | Точка монтування в контейнері |
| `strategy.maxSurge` / `maxUnavailable` | `1` / `0` | — | Параметри RollingUpdate |
| `terminationGracePeriodSeconds` | `10` | — | Час на коректне завершення |
| `probes.*` | `/health`, затримки 10/3 с | — | Liveness/readiness проби |
| `securityContext` | non-root `10001`, drop ALL | — | Безпека контейнера |
| `hooks.preUpgrade.enabled` | `true` | — | Job-перевірка `/health` перед upgrade |
| `hooks.preUpgrade.image`, `tests.image` | `busybox:1.36` | — | Образи хука та тесту |

«—» означає, що у `values-prod.yaml` значення не перевизначено.

### Встановлення

Підготовка (один раз):

```powershell
winget install --id Helm.Helm --exact --version 3.20.0   # саме Helm 3; без --version ставиться Helm 4
# перевідкрийте термінал (у VS Code — перезапустіть VS Code), щоб оновився PATH
helm version
minikube start --driver=docker --kubernetes-version=v1.37.0
minikube addons enable ingress
minikube image load devopslab/orders:1.0.0
minikube image load devopslab/orders:1.1.0
kubectl delete -f k8s/        # прибрати реліз лабораторної №3
```

Dev (значення за замовчуванням + `values-dev.yaml`):

```powershell
helm install orders-dev ./helm/orders -n orders-dev --create-namespace -f helm/orders/values-dev.yaml
```

Prod (токен береться зі змінної середовища, у файлах його немає):

```powershell
$env:ORDERS_API_TOKEN = "<токен із сховища секретів>"
helm install orders-prod ./helm/orders -n orders-prod --create-namespace -f helm/orders/values-prod.yaml --set secret.apiToken=$env:ORDERS_API_TOKEN
```

Перевірки та тест релізу:

```powershell
helm lint ./helm/orders -f helm/orders/values-prod.yaml
helm template orders-dev ./helm/orders -f helm/orders/values-dev.yaml
helm test orders-dev -n orders-dev
helm uninstall orders-dev -n orders-dev
```

### Пріоритет значень

Від найнижчого до найвищого: `values.yaml` чарта → файли `-f/--values`
(кожен наступний перекриває попередній) → `--set`/`--set-string`/`--set-file`
(праві перекривають ліві). При `helm upgrade` без `--reuse-values` значення
попередньої ревізії не успадковуються — береться `values.yaml` плюс те, що
передано в цій команді.

## Звіти

- Лабораторна №4 — інструкція з розташуванням кожного підпункту:
  [helm/lab4-guide.docx](./helm/lab4-guide.docx); звіт за пунктами 6–9 з місцями
  для скриншотів: [helm/lab4.docx](./helm/lab4.docx).
