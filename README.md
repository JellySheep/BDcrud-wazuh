# Единый стек: BDcrud3 + Wazuh (single-node)

## Структура
- `BDcrud3/` — проект BDcrud (приложение + postgres + mongo + nginx)
- `wazuh-docker/` — Wazuh docker repo
- `logs/nginx/` — общая папка логов nginx (её читает Wazuh)
- `docker-compose.yml` — единый compose

## Запуск
Из корня папки (где лежит `docker-compose.yml`):

```bash
# на всякий случай, чтобы file-bind маппинги были корректными
mkdir -p ./logs/nginx
touch ./logs/nginx/access_json.log ./logs/nginx/error_json.log

# старт
docker compose up -d --build

# проверить
docker compose ps
```

## Доступ
- BDcrud:
  - HTTP: `http://<host>:8008` (nginx из `BDcrud3/nginx/nginx.conf`)
  - HTTPS: `https://<host>:4443`
  - API напрямую (без nginx): `http://<host>:8000`

- Wazuh Dashboard:
  - `https://<host>/` (порт 443)

## Важно
1) В `docker-compose.yml` у postfix оставлены заглушки `RELAYHOST_USERNAME=MAIL` и `RELAYHOST_PASSWORD=PASSWORD` — подставьте реальные данные.
2) Если у вас на хосте уже занят 443 порт — измените маппинг в сервисе `wazuh.dashboard` (например на `5601:5601`).
