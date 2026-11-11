from __future__ import annotations

from datetime import date
from typing import Any

from django.conf import settings
from django.db import models

from apps.common.managers import OwnedManager
from apps.common.models import UUIDModel

KENYA_COUNTIES = [
    "Baringo",
    "Bomet",
    "Bungoma",
    "Busia",
    "Elgeyo-Marakwet",
    "Embu",
    "Garissa",
    "Homa Bay",
    "Isiolo",
    "Kajiado",
    "Kakamega",
    "Kericho",
    "Kiambu",
    "Kilifi",
    "Kirinyaga",
    "Kisii",
    "Kisumu",
    "Kitui",
    "Kwale",
    "Laikipia",
    "Lamu",
    "Machakos",
    "Makueni",
    "Mandera",
    "Marsabit",
    "Meru",
    "Migori",
    "Mombasa",
    "Murang'a",
    "Nairobi",
    "Nakuru",
    "Nandi",
    "Narok",
    "Nyamira",
    "Nyandarua",
    "Nyeri",
    "Samburu",
    "Siaya",
    "Taita-Taveta",
    "Tana River",
    "Tharaka-Nithi",
    "Trans Nzoia",
    "Turkana",
    "Uasin Gishu",
    "Vihiga",
    "Wajir",
    "West Pokot",
]

COUNTY_CHOICES = [(county, county) for county in KENYA_COUNTIES]


class Business(UUIDModel):
    class Sector(models.TextChoices):
        RETAIL = "retail", "Retail / shop"
        FOOD = "food_beverage", "Food & beverage"
        AGRIBUSINESS = "agribusiness", "Agribusiness"
        TRANSPORT = "transport", "Transport / logistics"
        SERVICES = "services", "Services"
        MANUFACTURING = "manufacturing", "Manufacturing"
        CONSTRUCTION = "construction", "Construction"
        TECH = "tech", "Tech / digital"
        HEALTH = "health", "Health"
        EDUCATION = "education", "Education"
        HOSPITALITY = "hospitality", "Hospitality"
        OTHER = "other", "Other"

    class Structure(models.TextChoices):
        SOLE_PROPRIETOR = "sole_proprietor", "Sole proprietor"
        PARTNERSHIP = "partnership", "Partnership"
        LIMITED_COMPANY = "limited_company", "Limited company"
        SACCO_GROUP = "sacco_group", "SACCO / group"
        OTHER = "other", "Other"

    class EmployeeBand(models.TextChoices):
        ZERO = "0", "0"
        ONE_TO_FIVE = "1-5", "1–5"
        SIX_TO_TWENTY = "6-20", "6–20"
        TWENTY_ONE_TO_FIFTY = "21-50", "21–50"
        FIFTY_PLUS = "50+", "50+"

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="business"
    )
    name = models.CharField(max_length=255)
    trading_name = models.CharField(max_length=255, blank=True)
    sector = models.CharField(max_length=40, choices=Sector.choices)
    what_they_sell = models.CharField(max_length=500, blank=True)
    county = models.CharField(max_length=40, choices=COUNTY_CHOICES)
    town = models.CharField(max_length=120, blank=True)
    started_on = models.DateField()
    structure = models.CharField(max_length=40, choices=Structure.choices)
    employee_band = models.CharField(max_length=10, choices=EmployeeBand.choices)
    owner_name = models.CharField(max_length=255)
    owner_phone = models.CharField(max_length=32)

    objects = OwnedManager()
    owner_lookup = "owner_id"

    class Meta:
        verbose_name_plural = "businesses"

    def __str__(self) -> str:
        return self.name

    @property
    def years_operating(self) -> float:
        return (date.today() - self.started_on).days / 365.25

    @property
    def months_operating(self) -> int:
        return int((date.today() - self.started_on).days / 30.44)

    def required_profile_fields(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "sector": self.sector,
            "what_they_sell": self.what_they_sell,
            "county": self.county,
            "town": self.town,
            "started_on": self.started_on,
            "structure": self.structure,
            "employee_band": self.employee_band,
            "owner_name": self.owner_name,
            "owner_phone": self.owner_phone,
        }
