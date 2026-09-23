# Лабораторна робота №2: Continuous Integration

Демонстраційний мікросервісний проєкт містить два незалежні Flask-сервіси:

- `users` — `http://localhost:8000/health` та `http://localhost:8000/users`;
- `orders` — `http://localhost:8001/health` та `http://localhost:8001/orders`.

## Локальний запуск

Потрібні Python 3.12 та Docker Desktop.

```powershell
py -m pip install -r services/users/requirements-dev.txt
py -m pip install -r services/orders/requirements-dev.txt
py -m ruff check services
py -m pytest services/users services/orders
docker compose up --build
```

## Публікація на GitHub

1. Створіть порожній репозиторій на GitHub, наприклад `devops-lab-2`.
2. У PowerShell з кореня цього проєкту виконайте:

```powershell
git init
git add .
git commit -m "Add CI pipeline for microservices"
git branch -M main
git remote add origin https://github.com/<ваш-логін>/devops-lab-2.git
git push -u origin main
```

3. Відкрийте вкладку **Actions** і переконайтеся, що jobs `users`, `orders`,
   `container-build` та `publish` завершилися успішно.
4. Для перевірки PR створіть гілку, внесіть зміну та відкрийте Pull Request у
   `main`. GitHub покаже статуси workflow безпосередньо у PR.

## Branch protection

У GitHub відкрийте **Settings > Rules > Rulesets** або **Settings > Branches**
та створіть правило для `main`:

- забороніть direct push і вимагайте Pull Request;
- увімкніть **Require a pull request before merging**;
- увімкніть **Require status checks to pass before merging**;
- після першого запуску додайте checks `Users - lint, build, test`,
  `Orders - lint, build, test` і `Build and scan ... image`;
- увімкніть вимогу актуальної гілки перед злиттям.

Для демонстрації заблокованого PR у тестовій гілці додайте синтаксичну помилку
або змініть очікуваний статус у тесті. PR буде позначено як failed і кнопка
злиття залишиться заблокованою. Після демонстрації виправте зміну.

## Образи GHCR

Для push у `main` workflow публікує кожен образ із двома тегами:

- `ghcr.io/<owner>/<repo>/users:<commit-sha>`;
- `ghcr.io/<owner>/<repo>/users:latest`;
- аналогічно для `orders`.

Переглянути їх можна у профілі GitHub у **Packages**. Для перевірки локально:

```powershell
docker login ghcr.io
docker pull ghcr.io/<owner>/<repo>/users:latest
docker run --rm -p 8000:8000 ghcr.io/<owner>/<repo>/users:latest
```

Потім відкрийте `http://localhost:8000/health`. Для приватного пакета потрібен
GitHub token із правом `read:packages`; токени не записуються в репозиторій.