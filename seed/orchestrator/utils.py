"""Small safe helpers for idempotent seed factories."""

from datetime import date, datetime, time, timedelta
from decimal import Decimal
import random

from django.contrib.auth.models import Group, User
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone


CITY_COORDS = {
    "HN": (21.0278, 105.8342),
    "DN": (16.0544, 108.2022),
    "HCM": (10.8231, 106.6297),
}

INDUSTRIES = ["Nhà máy", "Logistics", "Bệnh viện", "Trường học", "Chung cư", "Trung tâm thương mại"]


def vn_phone(index: int) -> str:
    return "09" + f"{index % 100000000:08d}"


def internal_email(prefix: str, index: int) -> str:
    return f"{prefix.lower()}.{index:06d}@scmdpro.local"


def fake_cccd(index: int, province: str = "001") -> str:
    # 12 numeric characters. Prefixes are synthetic and not tied to real people.
    return f"{province}{index % 10}{index % 100000000:08d}"


def jitter(base_lat: float, base_lng: float, meters: int = 1500):
    offset = meters / 111000.0
    return base_lat + random.uniform(-offset, offset), base_lng + random.uniform(-offset, offset)


def point_from_lat_lng(lat: float, lng: float):
    return Point(float(lng), float(lat), srid=4326)


def aware(dt: datetime):
    return timezone.make_aware(dt) if timezone.is_naive(dt) else dt


def month_iter(months: int):
    today = date.today().replace(day=1)
    for i in range(months - 1, -1, -1):
        year = today.year
        month = today.month - i
        while month <= 0:
            month += 12
            year -= 1
        yield year, month


def save_validated(obj, *, update_fields=None):
    # full_clean catches FK/null/choice/unique validation before DB write.
    obj.full_clean()
    obj.save(update_fields=update_fields)
    return obj


def get_group(name: str):
    return Group.objects.get_or_create(name=name)[0]


def get_user(username: str, email: str, password: str = "DigitalTwin@2026!"):
    user, created = User.objects.get_or_create(
        username=username,
        defaults={"email": email, "is_active": True},
    )
    if created:
        user.set_password(password)
        user.save(update_fields=["password"])
    elif user.email != email:
        user.email = email
        user.save(update_fields=["email"])
    return user


def decimal_vnd(value: int) -> Decimal:
    return Decimal(str(value))
