from django.db import models
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone


class TransmissionType(models.TextChoices):
    MANUAL = "manual", "Manual"
    AUTOMATIC = "automatic", "Automatic"


class Manager(models.Model):
    ssn_validator = RegexValidator(
        regex=r"^\d{3}-\d{2}-\d{4}$", message="SSN must be in the format XXX-XX-XXXX"
    )
    ssn = models.CharField(
        primary_key=True,
        max_length=11,
        validators=[ssn_validator],
        help_text="SSN (XXX-XX-XXXX), used for login.",
    )
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=120, unique=True)

    def __str__(self):
        return f"{self.name} ({self.ssn})"

    class Meta:
        verbose_name = "Manager"
        verbose_name_plural = "Managers"


class Client(models.Model):
    email = models.EmailField(
        primary_key=True, max_length=120, help_text="Client email, used for login."
    )
    name = models.CharField(max_length=100)
    addresses = models.ManyToManyField(
        "Address", through="ClientAddress", related_name="clients"
    )  # Client must have >= 1 address (enforced in forms/views)
    credit_cards = models.ManyToManyField(
        "CreditCard", related_name="client_owner"
    )  # Client must have >= 1 card (enforced in forms/views)

    def __str__(self):
        return f"{self.name} ({self.email})"

    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"


class Address(models.Model):
    address_id = models.AutoField(primary_key=True)
    road_name = models.CharField(max_length=120)
    number = models.CharField(max_length=20)
    city = models.CharField(max_length=80)

    def __str__(self):
        return f"{self.number} {self.road_name}, {self.city}"

    class Meta:
        verbose_name = "Address"
        verbose_name_plural = "Addresses"
        unique_together = [
            ["road_name", "number", "city"]
        ]  # Ensure addresses are unique physically


class ClientAddress(models.Model):
    """Junction table for Client-Address M:N relationship"""

    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.CASCADE)

    class Meta:
        unique_together = [
            ["client", "address"]
        ]  # Each client can only have a specific address once
        verbose_name = "Client Address Link"
        verbose_name_plural = "Client Address Links"


class CreditCard(models.Model):
    card_number_validator = RegexValidator(
        regex=r"^\d{16}$", message="Card number must be 16 digits."
    )
    card_number = models.CharField(
        primary_key=True, max_length=16, validators=[card_number_validator]
    )
    # client_email = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='owned_credit_cards') # Corrected link via ManyToManyField on Client
    payment_addr = models.ForeignKey(
        Address,
        on_delete=models.RESTRICT,
        help_text="Payment address for this card. Cannot delete address if used by card.",
    )  # Each card must have one payment address

    def __str__(self):
        # Mask card number for display
        return f"**** **** **** {self.card_number[-4:]}"

    class Meta:
        verbose_name = "Credit Card"
        verbose_name_plural = "Credit Cards"


class Car(models.Model):
    car_id = models.AutoField(primary_key=True)
    brand = models.CharField(max_length=80)

    def __str__(self):
        return self.brand

    class Meta:
        verbose_name = "Car Brand"
        verbose_name_plural = "Car Brands"


class Model(models.Model):
    # Weak entity: identified by (car, model_id)
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="models")
    model_id = models.IntegerField(
        help_text="Model identifier, unique within a car brand."
    )
    color = models.CharField(max_length=40)
    construction_year = models.SmallIntegerField(
        validators=[
            MinValueValidator(1900),
            MaxValueValidator(timezone.now().year + 1),
        ],
        help_text="Year between 1900 and next year.",
    )
    transmission = models.CharField(
        max_length=10, choices=TransmissionType.choices, default=TransmissionType.MANUAL
    )

    def __str__(self):
        return f"{self.car.brand} - Model {self.model_id} ({self.color}, {self.get_transmission_display()})"

    class Meta:
        # Enforce the composite key uniqueness
        unique_together = [["car", "model_id"]]
        verbose_name = "Car Model"
        verbose_name_plural = "Car Models"
        ordering = ["car__brand", "model_id"]


class Driver(models.Model):
    name = models.CharField(
        primary_key=True,
        max_length=100,
        help_text="Unique driver name, used for login.",
    )
    # A driver has exactly one address, and an address belongs to at most one driver.
    address = models.OneToOneField(
        Address,
        on_delete=models.RESTRICT,
        related_name="driver_resident",
        help_text="Driver's unique address. Cannot delete address if a driver lives there.",
    )
    drives_models = models.ManyToManyField(
        Model, through="Drives", related_name="drivers_certified"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Driver"
        verbose_name_plural = "Drivers"
        ordering = ["name"]


class Drives(models.Model):
    """Junction table for Driver-Model M:N relationship"""

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE)
    model = models.ForeignKey(Model, on_delete=models.CASCADE)

    class Meta:
        unique_together = [
            ["driver", "model"]
        ]  # Driver can only be certified for a model once
        verbose_name = "Driver Certification"
        verbose_name_plural = "Driver Certifications"


class Rent(models.Model):
    rent_id = models.AutoField(primary_key=True)
    rent_date = models.DateField()
    client = models.ForeignKey(
        Client,
        on_delete=models.RESTRICT,
        related_name="rents",
        help_text="Client who booked the rent. Cannot delete client if they have rents.",
    )
    driver = models.ForeignKey(
        Driver,
        on_delete=models.RESTRICT,
        related_name="rents",
        help_text="Driver assigned to the rent. Cannot delete driver if they have rents.",
    )
    model = models.ForeignKey(
        Model,
        on_delete=models.RESTRICT,
        related_name="rents",
        help_text="Model used for the rent. Cannot delete model if it has been used in rents.",
    )

    # Note: The UNIQUE constraints from Phase 2 (driver+date, model+date)
    # are removed as per professor feedback. Availability logic is handled in views.

    def __str__(self):
        return f"Rent {self.rent_id} ({self.rent_date}) - Client: {self.client.name}, Driver: {self.driver.name}, Model: {self.model}"

    class Meta:
        verbose_name = "Rent"
        verbose_name_plural = "Rents"
        ordering = ["-rent_date", "client__name"]


class Review(models.Model):
    # Weak entity: identified by (driver, review_id)
    driver = models.ForeignKey(
        Driver, on_delete=models.CASCADE, related_name="reviews_received"
    )
    # review_id needs to be unique *within* a driver. Django's AutoField provides global uniqueness.
    # We will enforce the logical weak entity concept via relationships and potentially view logic.
    review_id_within_driver = models.AutoField(
        primary_key=True
    )  # Using AutoField PK for Django ease
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="reviews_written"
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Rating from 0 to 5.",
    )
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(
        auto_now_add=True
    )  # Keep track of when review was made

    def __str__(self):
        return f"Review for {self.driver.name} by {self.client.name} (Rating: {self.rating})"

    class Meta:
        # The SQL had UNIQUE(client_email, driver_name, review_id).
        # Since review_id_within_driver is globally unique, this is implicitly handled.
        # If only *one* review per client per driver ever allowed:
        # unique_together = [['driver', 'client']]
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
        ordering = ["-created_at"]
