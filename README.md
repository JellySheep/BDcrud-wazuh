# Единый стек BDcrud3 + Wazuh SIEM (single-node)

Репозиторий содержит **готовый лабораторный стенд «в поле воин»**:

- **BDcrud3** — REST API + PostgreSQL + MongoDB  
- **Nginx** (reverse-proxy) — HTTPS/HTTP входная точка + **JSON-логи**  
- **Wazuh** (single-node) — Manager + Indexer + Dashboard  
- **Postfix + `alert_mailer.py`** — отправка алертов Wazuh на почту

Ключевая идея — **Nginx пишет JSON-логи в `/var/log/nginx/*.log`, Wazuh читает эти файлы и поднимает алерты**, а при необходимости алерты отправляются на email.

---

## Структура репозитория

Т.к. лабораторная работа чисто учебная все секреты и пароли мы не трогали, они лежат в первозданном виде

Все секреты по путям ниже, их нужно менять СТРОГО ДО ПЕРВОГО ЗАПУСКА, либо обнулять контейнер, либо потом руками пихать внутрь


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

> Сертификат у Dashboard также self-signed — браузер может показать предупреждение.

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

- Email для алертов нужно менять внутри главного docker-compose в блоке постфикса (3 последние строчки) + вставить туда пароль (токен) из пункта выше
- `RELAYHOST_USERNAME` заменить с `MAIL` на ваш логин
- `wazuh-docker/secrets/postfix_relay_password.txt` заменить с `PASSWORD` на пароль приложения
- `ALLOWED_SENDER_DOMAINS` выставить по домену вашего адреса (часть после `@`), например: `mail.ru`, `list.ru`, `bk.ru`, `inbox.ru`, желательно, конечно, именно `mail.ru`, т.к. на нем тесты уже были проведены

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

## Замена сертификатов Nginx (TLS)

> Nginx использует файлы:  
> - `secrets/nginx.key` — приватный ключ  
> - `certs/nginx.crt` — публичный сертификат

1) Остановить контейнеры (рекомендовано, чтобы ключ точно перечитался):
```bash
docker compose down
```

2) Перегенерировать ключ/сертификат (self-signed на 365 дней):
```bash
mkdir -p secrets certs

openssl req -x509 -nodes -days 365   -newkey rsa:2048   -keyout secrets/nginx.key   -out certs/nginx.crt   -subj "/CN=localhost"
```

3) Поднять стенд заново:
```bash
docker compose up -d --build
```

4) Проверка, что HTTPS живой:
```bash
curl -k https://localhost/products
```

> Важно: если ключ/сертификат подключены как **Docker secrets**, то после замены файлов на хосте обязательно нужен `docker compose down` → `up`, чтобы секреты переподхватились корректно.

---

## Генерация “инцидентов” в nginx access_json.log (для алертов SIEM)

Команда ниже дописывает пачку **явно вредоносных** запросов в:
`/var/log/nginx/access_json.log`

```bash
sudo bash -c '

echo "{\"time\":\"2025-12-25T18:20:01+10:00\",\"remote_addr\":\"203.0.113.10\",\"host\":\"app.local\",\"method\":\"GET\",\"uri\":\"/search?q=%3Cscript%3Ealert(1)%3C%2Fscript%3E\",\"status\":400,\"bytes\":312,\"request_time\":0.012,\"http_user_agent\":\"Mozilla/5.0\",\"http_x_forwarded_for\":\"198.51.100.23\"}" >> /var/log/nginx/access_json.log

echo "{\"time\":\"2025-12-25T18:20:06+10:00\",\"remote_addr\":\"198.51.100.77\",\"host\":\"app.local\",\"method\":\"POST\",\"uri\":\"/login?user=admin%27%20OR%20%271%27%3D%271%27--&pass=x\",\"status\":401,\"bytes\":278,\"request_time\":0.031,\"http_user_agent\":\"sqlmap/1.7\",\"http_x_forwarded_for\":\"-\"}" >> /var/log/nginx/access_json.log

echo "{\"time\":\"2025-12-25T18:20:11+10:00\",\"remote_addr\":\"203.0.113.55\",\"host\":\"app.local\",\"method\":\"GET\",\"uri\":\"/download?file=..%2F..%2F..%2Fetc%2Fpasswd\",\"status\":403,\"bytes\":221,\"request_time\":0.008,\"http_user_agent\":\"curl/8.5.0\",\"http_x_forwarded_for\":\"10.0.0.5\"}" >> /var/log/nginx/access_json.log

echo "{\"time\":\"2025-12-25T18:20:15+10:00\",\"remote_addr\":\"192.0.2.44\",\"host\":\"app.local\",\"method\":\"GET\",\"uri\":\"/.git/config\",\"status\":404,\"bytes\":153,\"request_time\":0.006,\"http_user_agent\":\"Mozilla/5.0 (compatible; Nikto/2.5.0)\",\"http_x_forwarded_for\":\"-\"}" >> /var/log/nginx/access_json.log

echo "{\"time\":\"2025-12-25T18:20:20+10:00\",\"remote_addr\":\"198.51.100.120\",\"host\":\"app.local\",\"method\":\"GET\",\"uri\":\"/api?url=http%3A%2F%2F169.254.169.254%2Flatest%2Fmeta-data%2F\",\"status\":400,\"bytes\":245,\"request_time\":0.017,\"http_user_agent\":\"python-requests/2.31\",\"http_x_forwarded_for\":\"-\"}" >> /var/log/nginx/access_json.log

echo "{\"time\":\"2025-12-25T18:20:25+10:00\",\"remote_addr\":\"203.0.113.99\",\"host\":\"app.local\",\"method\":\"GET\",\"uri\":\"/index.php?page=%252e%252e%252f%252e%252e%252fetc%252fpasswd\",\"status\":403,\"bytes\":233,\"request_time\":0.010,\"http_user_agent\":\"Mozilla/5.0\",\"http_x_forwarded_for\":\"172.16.1.9\"}" >> /var/log/nginx/access_json.log

echo "{\"time\":\"2025-12-25T18:20:30+10:00\",\"remote_addr\":\"192.0.2.200\",\"host\":\"app.local\",\"method\":\"TRACE\",\"uri\":\"/\",\"status\":405,\"bytes\":128,\"request_time\":0.004,\"http_user_agent\":\"Mozilla/5.0\",\"http_x_forwarded_for\":\"-\"}" >> /var/log/nginx/access_json.log

echo "{\"time\":\"2025-12-25T18:20:35+10:00\",\"remote_addr\":\"198.51.100.66\",\"host\":\"app.local\",\"method\":\"GET\",\"uri\":\"/wp-login.php\",\"status\":404,\"bytes\":161,\"request_time\":0.005,\"http_user_agent\":\"Masscan/1.3\",\"http_x_forwarded_for\":\"-\"}" >> /var/log/nginx/access_json.log

'
```

Проверка, что записи реально появились:
```bash
sudo tail -n 20 /var/log/nginx/access_json.log
```

Дальше можно сразу смотреть алерты Wazuh:

```bash
docker compose exec wazuh.manager bash -lc 'tail -n 50 /var/ossec/logs/alerts/alerts.json'
```

Если нужно, чтобы алерты «вылетали» пачкой — добавить такие строки несколько раз (или дублируй блок с разными `time`/`remote_addr`).

