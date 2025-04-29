from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Manager,
    Client,
    Address,
    CreditCard,
    Car,
    Model,
    Driver,
    Drives,
    Rent,
    Review,
)
from django.utils import timezone


class ManagerForm(forms.ModelForm):
    class Meta:
        model = Manager
        fields = ["ssn", "name", "email"]
        widgets = {
            "ssn": forms.TextInput(attrs={"placeholder": "XXX-XX-XXXX"}),
        }


class ClientForm(forms.ModelForm):
    # Separate forms might be better for addresses/cards during registration
    class Meta:
        model = Client
        fields = ["email", "name"]


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ["road_name", "number", "city"]


class CreditCardForm(forms.ModelForm):
    # Need to associate with client and payment address in the view
    payment_addr = forms.ModelChoiceField(
        queryset=Address.objects.none(), label="Payment Address"
    )  # Queryset set in view

    class Meta:
        model = CreditCard
        fields = ["card_number", "payment_addr"]
        widgets = {
            "card_number": forms.TextInput(
                attrs={"placeholder": "16 digits, no spaces"}
            ),
        }

    def __init__(self, *args, **kwargs):
        client_addresses = kwargs.pop("client_addresses", None)
        super().__init__(*args, **kwargs)
        if client_addresses:
            self.fields["payment_addr"].queryset = client_addresses


class CarForm(forms.ModelForm):
    class Meta:
        model = Car
        fields = ["brand"]


class ModelForm(forms.ModelForm):
    class Meta:
        model = Model
        fields = ["car", "model_id", "color", "construction_year", "transmission"]
        labels = {"model_id": "Model Identifier (Unique within Brand)"}


class DriverForm(forms.ModelForm):
    # Address needs to be created/selected separately in the view
    class Meta:
        model = Driver
        fields = ["name"]  # Address handled separately


class DriverAddressForm(forms.ModelForm):
    # Used for updating driver's address
    class Meta:
        model = Address
        fields = ["road_name", "number", "city"]


class DrivesForm(forms.Form):
    # Select models a driver can drive
    models = forms.ModelMultipleChoiceField(
        queryset=Model.objects.all().order_by("car__brand", "model_id"),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )


class RentSearchForm(forms.Form):
    rent_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "min": timezone.now().date()})
    )


class BookRentForm(forms.Form):
    rent_date = forms.DateField(widget=forms.HiddenInput())  # Pre-filled from search
    model = forms.ModelChoiceField(
        queryset=Model.objects.none(), empty_label=None
    )  # Queryset of available models set in view
    use_best_driver = forms.BooleanField(
        required=False,
        label="Assign the highest-rated available driver? (Group of 4 feature)",
    )

    def __init__(self, *args, **kwargs):
        available_models_qs = kwargs.pop("available_models_qs", None)
        super().__init__(*args, **kwargs)
        if available_models_qs:
            self.fields["model"].queryset = available_models_qs


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "message"]
        widgets = {
            "rating": forms.NumberInput(attrs={"min": 0, "max": 5}),
            "message": forms.Textarea(attrs={"rows": 3}),
        }


# --- Manager Report Forms ---


class TopKClientsForm(forms.Form):
    k = forms.IntegerField(min_value=1, label="Number of top clients (k)")


class CrossCityClientsForm(forms.Form):
    city1 = forms.CharField(max_length=80, label="Client Address City (C1)")
    city2 = forms.CharField(max_length=80, label="Driver Address City (C2)")
