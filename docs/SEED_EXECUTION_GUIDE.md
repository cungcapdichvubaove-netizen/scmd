# SCMD Pro Demo Seed Execution Guide — KTC Việt Nam Security Group (V4 Light)

Tài liệu này dùng cho staging/demo của SCMD Pro khi cần trình diễn cho KTC Việt Nam Security Group trên VM cấu hình thấp.

## Profile mặc định

`seed_scmd_demo` mặc định dùng profile `light` để phù hợp server demo hiện tại:

```text
profile: light
guards: 60
days: 21
past-days: 7
targets: 24
incidents: 36
headcount checks: 72
inventory issue slips: 16
payroll periods: 1
```

Profile khác:

```text
standard: 80 guards / 30 days / 10 past-days
full: 200 guards / 45 days / 15 past-days
```

Chỉ dùng `full` khi VM có tối thiểu 4GB RAM hoặc chạy benchmark nội bộ.

## Mật khẩu demo

Mật khẩu mặc định cho toàn bộ tài khoản demo staging:

```text
Abcd@1234
```

Có thể override bằng `--password`, nhưng không nên in mật khẩu trong log hoặc tài liệu gửi khách hàng.

## Lệnh chạy trong Docker staging

Backup DB trước:

```bash
cd /opt/scmdpro
mkdir -p backups

docker compose -f docker-compose.prod.yml -f docker-compose.staging.yml exec -T db \
  pg_dump -U scmd -d scmdpro -Fc > backups/scmdpro_before_demo_seed_$(date +%Y%m%d_%H%M%S).dump
```

Dry-run:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.staging.yml run --rm web \
  python manage.py seed_scmd_demo --scenario ktc_viet_nam_security_group --dry-run
```

Seed thật bằng profile mặc định `light`:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.staging.yml run --rm web \
  python manage.py seed_scmd_demo --scenario ktc_viet_nam_security_group
```

Seed có override rõ ràng:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.staging.yml run --rm web \
  python manage.py seed_scmd_demo \
  --scenario ktc_viet_nam_security_group \
  --profile light \
  --guards 60 \
  --days 21 \
  --past-days 7 \
  --password 'Abcd@1234'
```

Reset dữ liệu demo KTCVN rồi seed lại:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.staging.yml run --rm web \
  python manage.py seed_scmd_demo \
  --scenario ktc_viet_nam_security_group \
  --reset-demo \
  --confirm-reset
```

Cập nhật CompanyInfo chỉ khi đây là DB demo cô lập:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.staging.yml run --rm web \
  python manage.py seed_scmd_demo \
  --scenario ktc_viet_nam_security_group \
  --update-company-info
```

## Quy trình khuyến nghị trên VM 1GB RAM

```bash
cd /opt/scmdpro

docker compose -f docker-compose.prod.yml -f docker-compose.staging.yml stop web nginx celery celery_beat

docker compose -f docker-compose.prod.yml -f docker-compose.staging.yml up -d db redis

docker compose -f docker-compose.prod.yml -f docker-compose.staging.yml run --rm web \
  python manage.py seed_scmd_demo --scenario ktc_viet_nam_security_group --dry-run

docker compose -f docker-compose.prod.yml -f docker-compose.staging.yml run --rm web \
  python manage.py seed_scmd_demo --scenario ktc_viet_nam_security_group

docker compose -f docker-compose.prod.yml -f docker-compose.staging.yml up -d web nginx celery celery_beat
```

## Kiểm tra sau seed

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.staging.yml exec web python manage.py check

docker compose -f docker-compose.prod.yml -f docker-compose.staging.yml exec web python manage.py makemigrations --check --dry-run

curl -i --max-time 30 http://127.0.0.1/
curl -i --max-time 30 http://127.0.0.1/api/v1/health/
```

Kỳ vọng:

```text
/: 302 Location: /login/
/api/v1/health/: 200 OK
```
