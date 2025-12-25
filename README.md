# Единый стек BDcrud3 + Wazuh SIEM (single-node)

Репозиторий содержит **готовый лабораторный стенд «в поле воин»**:

- **BDcrud3** — REST API + PostgreSQL + MongoDB  
- **Nginx** (reverse-proxy) — HTTPS/HTTP входная точка + **JSON-логи** запросов  
- **Wazuh** (single-node) — Manager + Indexer + Dashboard  
- **Postfix + `alert_mailer.py`** — отправка алертов Wazuh на почту

Ключевая идея стенда — **Nginx пишет JSON-логи в `/var/log/nginx/*.log`, Wazuh читает эти файлы и поднимает алерты**, а при необходимости алерты отправляются на email.

---

## Требования

1) **Linux-хост** (желательно). В compose используется `network_mode: host` для Nginx и bind-mount на `/var/log/nginx`.  
2) Установлены **Docker Engine** и **Docker Compose v2** (команда `docker compose`).  
3) Свободные порты на хосте:
   - `443` — Wazuh Dashboard
   - `4443` — HTTPS для BDcrud (Nginx)
   - `8008` — HTTP для BDcrud (Nginx)
   - `8000` — API BDcrud напрямую
   - `9200` — Wazuh Indexer (OpenSearch)
   - `1514/1515/55000` и др. — сервисные порты Wazuh

4) Для Wazuh Indexer (OpenSearch) на Linux нужно повысить лимит:
```bash
sudo sysctl -w vm.max_map_count=262144
```
Чтобы сохранить после перезагрузки — добавьте `vm.max_map_count=262144` в `/etc/sysctl.conf` и примените `sudo sysctl -p`.


---

## Структура репозитория

- `docker-compose.yml` — **единый** compose для всего стенда
- `BDcrud3/` — приложение + postgres + mongo + nginx-конфиг + сертификаты/секреты BDcrud
  - `BDcrud3/nginx/nginx.conf` — конфиг Nginx (формат логов JSON, порты 8008/4443)
  - `BDcrud3/secrets/postgres_password.txt` — пароль Postgres (Docker secret)
  - `BDcrud3/secrets/nginx.key` — приватный ключ TLS для Nginx (Docker secret)
  - `BDcrud3/certs/nginx.crt` — сертификат TLS (self-signed, CN=localhost)
- `wazuh-docker/` — файлы Wazuh (single-node) + секреты
  - `wazuh-docker/secrets/*.txt` — пароли Wazuh и пароль SMTP relay (Docker secrets)
  - `wazuh-docker/secrets/*.pem` — приватные ключи Wazuh (Docker secrets)
  - `wazuh-docker/single-node/config/...` — конфиги Wazuh, включая чтение nginx-логов

---

## Быстрый старт (одна команда)

Из корня репозитория.

### 1) Подготовить nginx-логи на хосте

> Важно: Nginx пишет логи **в `/var/log/nginx` на хосте** (это mount в контейнер).  
> Создайте директорию и файлы, выдайте права на запись.

```bash
sudo mkdir -p /var/log/nginx
sudo touch /var/log/nginx/access_json.log /var/log/nginx/error_json.log

# В официальном nginx образе пользователь nginx обычно имеет UID 101
sudo chown -R 101:101 /var/log/nginx
sudo chmod 755 /var/log/nginx
```

### 2) Запустить стек

```bash
docker compose up -d --build
docker compose ps
```

Логи сервисов (при необходимости):

```bash
docker compose logs -f wazuh.manager
docker compose logs -f wazuh.indexer
docker compose logs -f wazuh.dashboard
```

---

## Доступы

### BDcrud3

- HTTP: `http://localhost:8008/`
- HTTPS: `https://localhost:4443/`
- API напрямую (без Nginx): `http://localhost:8000/`

> TLS для BDcrud self-signed, поэтому для `curl` используйте `-k`.

Тестовый запрос (создать продукт):

```bash
curl -k -X POST https://localhost:4443/products \
  -H "Content-Type: application/json" \
  -d '{"name":"TestBD","description":"from_lab_test","price":222.0,"qty":333,"category":"lab"}'
```

Проверить список:

```bash
curl -k https://localhost:4443/products
```

### Wazuh Dashboard

- URL: `https://localhost/` (порт 443)

Учетные данные (по умолчанию, из конфигов/секретов репозитория):
- **admin / SecretPassword**

> Сертификат у Dashboard также self-signed — браузер покажет предупреждение.

---

## Как устроены пароли и Docker secrets

В проекте секреты читаются из файлов и прокидываются в контейнеры как **Docker secrets** (см. блок `secrets:` в `docker-compose.yml`).

### PostgreSQL (BDcrud3)

- Пароль хранится в: `BDcrud3/secrets/postgres_password.txt`
- PostgreSQL использует `POSTGRES_PASSWORD_FILE` (инициализация при первом старте volume `pgdata`)
- Приложение **читает тот же secret** и на старте собирает `POSTGRES_DSN` (см. `BDcrud3/app/entrypoint.sh`)

Важно:
- **Пароль “фиксируется” на первом запуске**, когда создается volume `pgdata`.
- Если поменяли `postgres_password.txt`, а база уже инициализирована — проще всего пересоздать volume:

```bash
docker compose down -v
docker compose up -d --build
```

### Wazuh / Postfix

Файлы секретов лежат в `wazuh-docker/secrets/`:

- `wazuh_indexer_password.txt` (по умолчанию `SecretPassword`)
- `wazuh_api_password.txt` (по умолчанию `MyS3cr37P450r.*-`)
- `wazuh_dashboard_password.txt` (по умолчанию `kibanaserver`)
- `postfix_relay_password.txt` — пароль приложения SMTP (по умолчанию заглушка `PASSWORD`)

Важно:
- После изменения файла секрета требуется **перезапуск** контейнера/сервиса (минимум — `docker compose restart <service>`).

---

## Почтовые алерты (Mail.ru / list.ru / bk.ru / inbox.ru)

Схема работы:

1) `wazuh.manager` пишет алерты в `/var/ossec/logs/alerts/alerts.log`
2) контейнер `wazuh-alert-mailer` читает файл и отправляет письма через `wazuh-postfix`
3) `wazuh-postfix` делает relay в ваш SMTP (по умолчанию `smtp.mail.ru:587`)

### 1) Создать пароль приложения в Mail.ru

В почте Mail.ru: **Профиль → Пароли и безопасность → Пароли для внешних приложений → создать пароль** (SMTP/IMAP/POP3).

### 2) Настроить Postfix (relay)

Файл: `docker-compose.yml`, сервис `postfix`.

Что нужно сделать:

- `RELAYHOST_USERNAME` заменить с `MAIL` на ваш логин (чаще всего это email целиком)
- `wazuh-docker/secrets/postfix_relay_password.txt` заменить с `PASSWORD` на пароль приложения
- `ALLOWED_SENDER_DOMAINS` выставить по домену вашего адреса (часть после `@`), например: `mail.ru`, `list.ru`, `bk.ru`, `inbox.ru`

После правок перезапустите postfix:

```bash
docker compose up -d postfix
```

### 3) Настроить отправителя/получателя в alert_mailer.py

Файл: `wazuh-docker/single-node/alert_mailer.py`

Замените значения:

```python
MAIL_FROM = "MAIL"
MAIL_TO = ["PASSWORD"]
```

на свои, например:

```python
MAIL_FROM = "user@list.ru"
MAIL_TO = ["user@list.ru"]
```

Пересоберите и перезапустите mailer:

```bash
docker compose build wazuh-alert-mailer
docker compose up -d wazuh-alert-mailer
```

### Диагностика отправки писем

Логи postfix:
```bash
docker compose logs -f postfix
```

Очередь писем в контейнере postfix:
```bash
docker exec -it wazuh-postfix mailq
# или
docker exec -it wazuh-postfix postqueue -p
```

---

## Где смотреть алерты Wazuh

В контейнере `wazuh.manager`:

- JSON-алерты: `/var/ossec/logs/alerts/alerts.json`
- Текстовые алерты: `/var/ossec/logs/alerts/alerts.log` *(его читает `wazuh-alert-mailer`)*

Команды:

```bash
docker compose exec wazuh.manager bash -lc 'tail -n 50 /var/ossec/logs/alerts/alerts.json'
docker compose exec wazuh.manager bash -lc 'tail -n 50 /var/ossec/logs/alerts/alerts.log'
```

Проверка декодинга/правил (Wazuh logtest):

```bash
docker compose exec wazuh.manager /var/ossec/bin/wazuh-logtest
```

---

## Nginx-логи (источник событий для SIEM)

Файлы на хосте:

- `/var/log/nginx/access_json.log`
- `/var/log/nginx/error_json.log`

Быстрая проверка, что Nginx пишет:

```bash
sudo tail -n 20 /var/log/nginx/access_json.log
sudo tail -n 20 /var/log/nginx/error_json.log
```

---

## Кастомные правила (local_rules.xml)

Файл:
- `wazuh-docker/single-node/config/wazuh_manager/local_rules/local_rules.xml`

В нем настроены базовые детекты (по содержимому Nginx JSON-логов), например:

- `100010` — HTTP 500
- `100011` — HTTP 403
- `100012` — HTTP 401
- `100013` — SQLi (`OR 1=1`, `UNION SELECT`, `sqlmap`)
- `100014` — path traversal / LFI (`..`, `/etc/passwd`, `/etc/shadow`)
- `100016` — сканеры/брут (`Hydra`, `Nikto`, `masscan`, `dirbuster`)
- `100017` — подозрительные User-Agent (`curl`, `Wget`, `python-requests`, `PostmanRuntime`)
- `100018` — попытки доступа к чувствительным файлам (`.env`, `.git/config`, `phpMyAdmin`)

Пример, чтобы гарантированно «дернуть» правило (LFI + подозрительный UA):

```bash
curl -k "https://localhost:4443/../../../../etc/passwd" -A "curl"
```

---

## Проверка актуальности `ossec.conf` в контейнере

В проекте конфиг подмонтирован в `/wazuh-config-mount/etc/ossec.conf`. Полезно убедиться, что в `/var/ossec/etc/ossec.conf` лежит актуальная версия.

```bash
docker compose exec wazuh.manager bash -lc '
ls -l /var/ossec/etc/ossec.conf /wazuh-config-mount/etc/ossec.conf; 
sha256sum /var/ossec/etc/ossec.conf /wazuh-config-mount/etc/ossec.conf'
```

Если нужно принудительно обновить и перезапустить Wazuh:

```bash
docker compose exec wazuh.manager bash -lc '
cp -f /wazuh-config-mount/etc/ossec.conf /var/ossec/etc/ossec.conf && 
/var/ossec/bin/wazuh-control restart'
```

---

## Остановка / очистка

Остановить:

```bash
docker compose down
```

Полная очистка (включая БД и данные Wazuh):

```bash
docker compose down -v
```

---

## Перенос на другой ПК и сертификаты

Для **лабораторного стенда** в репозитории уже лежат:

- TLS сертификат для BDcrud (`BDcrud3/certs/nginx.crt`) и приватный ключ как secret (`BDcrud3/secrets/nginx.key`)
- сертификаты и ключи Wazuh в `wazuh-docker/single-node/config/wazuh_indexer_ssl_certs/` и `wazuh-docker/secrets/*.pem`

Поэтому при переносе, как правило, достаточно:

1) склонировать репозиторий
2) подготовить `/var/log/nginx` (см. «Быстрый старт»)
3) выполнить `docker compose up -d --build`

Если нужно **перегенерировать** сертификаты Wazuh:

```bash
cd wazuh-docker/single-node
docker compose -f generate-indexer-certs.yml run --rm generator
```

После генерации убедитесь, что приватные ключи, которые подключаются как Docker secrets, лежат в `wazuh-docker/secrets/` (имена файлов должны совпадать с теми, что указаны в `docker-compose.yml`).

---

## Замечание по безопасности

В репозитории присутствуют **лабораторные** пароли/ключи/сертификаты. Для публичных репозиториев и реальных сред:

- не храните приватные ключи и пароли в Git
- используйте `.gitignore` и внешнее секрет-хранилище / CI variables / Docker secrets «извне»
