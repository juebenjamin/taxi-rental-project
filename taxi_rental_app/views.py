from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.db.models import (
    Count,
    Avg,
    Q,
    Subquery,
    OuterRef,
    F,
    ExpressionWrapper,
    FloatField,
)
from django.db import transaction, IntegrityError
import django
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


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
    ClientAddress,
)
from .forms import (
    ManagerForm,
    ClientForm,
    AddressForm,
    CreditCardForm,
    CarForm,
    ModelForm,
    DriverForm,
    DriverAddressForm,
    DrivesForm,
    RentSearchForm,
    BookRentForm,
    ReviewForm,
    TopKClientsForm,
    CrossCityClientsForm,
)
import random  # For assigning random driver

# --- Mock Auth & Role Handling ---


def set_user_role(request, role, identifier):
    """Mock setting user role in session"""
    request.session["user_role"] = role
    request.session["user_identifier"] = identifier  # e.g., ssn, email, name


def get_user_role(request):
    """Mock getting user role from session"""
    role = request.session.get("user_role")
    identifier = request.session.get("user_identifier")
    user = None
    if role == "manager":
        try:
            user = Manager.objects.get(pk=identifier)
        except Manager.DoesNotExist:
            role = None
    elif role == "client":
        try:
            user = Client.objects.get(pk=identifier)
        except Client.DoesNotExist:
            role = None
    elif role == "driver":
        try:
            user = Driver.objects.get(pk=identifier)
        except Driver.DoesNotExist:
            role = None
    else:
        role = None

    return role, user


def mock_login(request):
    if request.method == "POST":
        role = request.POST.get("role")
        identifier = request.POST.get("identifier")

        # Basic validation (in real app, check credentials)
        user_exists = False
        redirect_url = reverse("taxi_rental_app:index")

        if role == "manager":
            if Manager.objects.filter(pk=identifier).exists():
                user_exists = True
                redirect_url = reverse("taxi_rental_app:manager_dashboard")
        elif role == "client":
            if Client.objects.filter(pk=identifier).exists():
                user_exists = True
                redirect_url = reverse(
                    "taxi_rental_app:client_dashboard",
                    kwargs={"client_email": identifier},
                )
        elif role == "driver":
            if Driver.objects.filter(pk=identifier).exists():
                user_exists = True
                redirect_url = reverse(
                    "taxi_rental_app:driver_dashboard",
                    kwargs={"driver_name": identifier},
                )

        if user_exists:
            set_user_role(request, role, identifier)
            messages.success(request, f"Logged in as {role}: {identifier}")
            return redirect(redirect_url)
        else:
            messages.error(request, "Invalid identifier for selected role.")
            return redirect("taxi_rental_app:login")

    # If GET request, show login form
    managers = Manager.objects.all()
    clients = Client.objects.all()
    drivers = Driver.objects.all()
    return render(
        request,
        "taxi_rental_app/auth/login.html",
        {
            "managers": managers,
            "clients": clients,
            "drivers": drivers,
        },
    )


def mock_logout(request):
    """Mock logging out"""
    request.session.flush()  # Clear session
    messages.info(request, "You have been logged out.")
    return redirect("taxi_rental_app:index")


# --- Decorators for Role Checks (Basic Example) ---
def role_required(allowed_roles):
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            role, user = get_user_role(request)
            if role not in allowed_roles or user is None:
                messages.error(
                    request, "Access denied. Please log in with the correct role."
                )
                return redirect("taxi_rental_app:login")  # Or an access denied page
            # Pass user object to the view if needed
            kwargs["current_user"] = user
            kwargs["current_role"] = role
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


# --- General Views ---


def index(request):
    """Home page"""
    role, user = get_user_role(request)
    return render(
        request,
        "taxi_rental_app/index.html",
        {"current_role": role, "current_user": user},
    )


# --- Manager Views ---


@role_required(["manager"])
def manager_dashboard(request, current_user, current_role):
    # Add some stats for the dashboard
    num_drivers = Driver.objects.count()
    num_clients = Client.objects.count()
    num_cars = Car.objects.count()
    num_models = Model.objects.count()
    num_rents = Rent.objects.count()
    context = {
        "manager": current_user,
        "num_drivers": num_drivers,
        "num_clients": num_clients,
        "num_cars": num_cars,
        "num_models": num_models,
        "num_rents": num_rents,
    }
    return render(request, "taxi_rental_app/manager/dashboard.html", context)


# --- Car CRUD ---
@role_required(["manager"])
def manager_car_list(request, current_user, current_role):
    cars = Car.objects.all().order_by("brand")
    return render(request, "taxi_rental_app/manager/car_list.html", {"cars": cars})


@role_required(["manager"])
def manager_car_create(request, current_user, current_role):
    if request.method == "POST":
        form = CarForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request, f"Car brand '{form.cleaned_data['brand']}' added."
            )
            return redirect("taxi_rental_app:manager_car_list")
    else:
        form = CarForm()
    return render(
        request,
        "taxi_rental_app/manager/car_form.html",
        {"form": form, "action": "Add"},
    )


@role_required(["manager"])
def manager_car_update(request, pk, current_user, current_role):
    car = get_object_or_404(Car, pk=pk)
    if request.method == "POST":
        form = CarForm(request.POST, instance=car)
        if form.is_valid():
            form.save()
            messages.success(
                request, f"Car brand '{form.cleaned_data['brand']}' updated."
            )
            return redirect("taxi_rental_app:manager_car_list")
    else:
        form = CarForm(instance=car)
    return render(
        request,
        "taxi_rental_app/manager/car_form.html",
        {"form": form, "action": "Edit"},
    )


@role_required(["manager"])
def manager_car_delete(request, pk, current_user, current_role):
    car = get_object_or_404(Car, pk=pk)
    if request.method == "POST":
        brand_name = car.brand
        try:
            car.delete()
            messages.success(request, f"Car brand '{brand_name}' deleted.")
        except (
            django.db.models.ProtectedError
        ):  # Or IntegrityError if RESTRICT is used heavily
            messages.error(
                request,
                f"Cannot delete car brand '{brand_name}' as it has associated models.",
            )
        return redirect("taxi_rental_app:manager_car_list")
    return render(
        request,
        "taxi_rental_app/manager/confirm_delete.html",
        {"object": car, "object_type": "Car Brand"},
    )


# --- Model CRUD ---
@role_required(["manager"])
def manager_model_list(request, current_user, current_role):
    models_list = (
        Model.objects.select_related("car").all().order_by("car__brand", "model_id")
    )
    return render(
        request, "taxi_rental_app/manager/model_list.html", {"models": models_list}
    )


@role_required(["manager"])
def manager_model_create(request, current_user, current_role):
    if request.method == "POST":
        form = ModelForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f"Model '{form.instance}' added.")
                return redirect("taxi_rental_app:manager_model_list")
            except (
                IntegrityError
            ):  # Catches violation of unique_together (car, model_id)
                messages.error(
                    request,
                    f"A model with ID {form.cleaned_data['model_id']} already exists for car brand {form.cleaned_data['car']}. Please choose a unique ID.",
                )
    else:
        form = ModelForm()
    return render(
        request,
        "taxi_rental_app/manager/model_form.html",
        {"form": form, "action": "Add"},
    )


@role_required(["manager"])
def manager_model_update(request, car_pk, model_pk, current_user, current_role):
    # Composite PK requires fetching like this
    model_instance = get_object_or_404(Model, car_id=car_pk, model_id=model_pk)
    if request.method == "POST":
        form = ModelForm(request.POST, instance=model_instance)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, f"Model '{form.instance}' updated.")
                return redirect("taxi_rental_app:manager_model_list")
            except IntegrityError:
                messages.error(
                    request,
                    f"A model with ID {form.cleaned_data['model_id']} already exists for car brand {form.cleaned_data['car']}. Please choose a unique ID.",
                )
    else:
        form = ModelForm(instance=model_instance)
    # Prevent changing the car/model_id in the form to avoid PK issues during update
    form.fields["car"].disabled = True
    form.fields["model_id"].disabled = True
    return render(
        request,
        "taxi_rental_app/manager/model_form.html",
        {"form": form, "action": "Edit"},
    )


@role_required(["manager"])
def manager_model_delete(request, car_pk, model_pk, current_user, current_role):
    model_instance = get_object_or_404(Model, car_id=car_pk, model_id=model_pk)
    if request.method == "POST":
        model_str = str(model_instance)
        try:
            model_instance.delete()
            messages.success(request, f"Model '{model_str}' deleted.")
        except django.db.models.ProtectedError:
            messages.error(
                request,
                f"Cannot delete model '{model_str}' as it has associated rents or driver certifications.",
            )
        return redirect("taxi_rental_app:manager_model_list")
    return render(
        request,
        "taxi_rental_app/manager/confirm_delete.html",
        {"object": model_instance, "object_type": "Car Model"},
    )


# --- Driver CRUD ---
@role_required(["manager"])
def manager_driver_list(request, current_user, current_role):
    drivers = Driver.objects.select_related("address").all().order_by("name")
    return render(
        request, "taxi_rental_app/manager/driver_list.html", {"drivers": drivers}
    )


@role_required(["manager"])
@transaction.atomic  # Ensure driver and address are created/deleted together
def manager_driver_create(request, current_user, current_role):
    if request.method == "POST":
        driver_form = DriverForm(request.POST, prefix="driver")
        address_form = AddressForm(request.POST, prefix="address")
        if driver_form.is_valid() and address_form.is_valid():
            # Check if address already exists (to potentially reuse or prevent duplicates)
            # For simplicity here, we assume a new unique address per driver creation
            try:
                address = address_form.save()
                driver = driver_form.save(commit=False)
                driver.address = address
                driver.save()  # This might raise IntegrityError if name exists
                messages.success(request, f"Driver '{driver.name}' added.")
                return redirect("taxi_rental_app:manager_driver_list")
            except IntegrityError:  # Catches Driver name unique constraint
                messages.error(
                    request,
                    f"A driver with the name '{driver_form.cleaned_data['name']}' already exists.",
                )
                # If address was created but driver failed, delete orphaned address
                if (
                    "address" in locals()
                    and address.pk
                    and not Driver.objects.filter(address=address).exists()
                ):
                    address.delete()
            except Exception as e:
                messages.error(request, f"An error occurred: {e}")
                if (
                    "address" in locals()
                    and address.pk
                    and not Driver.objects.filter(address=address).exists()
                ):
                    address.delete()

    else:
        driver_form = DriverForm(prefix="driver")
        address_form = AddressForm(prefix="address")
    return render(
        request,
        "taxi_rental_app/manager/driver_form.html",
        {"driver_form": driver_form, "address_form": address_form, "action": "Add"},
    )


@role_required(["manager"])
@transaction.atomic
def manager_driver_update(request, pk, current_user, current_role):
    # PK is name (string)
    driver = get_object_or_404(Driver.objects.select_related("address"), pk=pk)
    address = driver.address
    if request.method == "POST":
        driver_form = DriverForm(
            request.POST, instance=driver, prefix="driver"
        )  # Name cannot be changed here as it's PK
        address_form = AddressForm(request.POST, instance=address, prefix="address")
        if driver_form.is_valid() and address_form.is_valid():
            try:
                address_form.save()  # Save address changes
                # Driver name (PK) shouldn't be changed easily, handle separately if needed
                # driver_form.save() # Only saves non-PK fields if needed
                messages.success(
                    request, f"Driver '{driver.name}' information updated."
                )
                return redirect("taxi_rental_app:manager_driver_list")
            except Exception as e:
                messages.error(request, f"An error occurred during update: {e}")
    else:
        driver_form = DriverForm(instance=driver, prefix="driver")
        address_form = AddressForm(instance=address, prefix="address")

    driver_form.fields["name"].disabled = True  # Disable PK field
    return render(
        request,
        "taxi_rental_app/manager/driver_form.html",
        {"driver_form": driver_form, "address_form": address_form, "action": "Edit"},
    )


@role_required(["manager"])
@transaction.atomic
def manager_driver_delete(request, pk, current_user, current_role):
    driver = get_object_or_404(Driver, pk=pk)
    address = driver.address  # Get address before deleting driver
    if request.method == "POST":
        driver_name = driver.name
        try:
            driver.delete()
            # Also delete the associated address if it's no longer used by anyone else (e.g., credit card)
            if not CreditCard.objects.filter(payment_addr=address).exists():
                address.delete()
            messages.success(
                request, f"Driver '{driver_name}' and associated address deleted."
            )
        except django.db.models.ProtectedError:
            messages.error(
                request,
                f"Cannot delete driver '{driver_name}' as they have associated rents or reviews.",
            )
        return redirect("taxi_rental_app:manager_driver_list")
    return render(
        request,
        "taxi_rental_app/manager/confirm_delete.html",
        {"object": driver, "object_type": "Driver"},
    )


# --- Manager Reports ---


@role_required(["manager"])
def manager_report_top_clients(request, current_user, current_role):
    """Report 4: Top-k clients by number of rents"""
    clients_data = None
    form = TopKClientsForm(request.GET or None)
    if form.is_valid():
        k = form.cleaned_data["k"]
        clients_data = (
            Client.objects.annotate(rent_count=Count("rents"))
            .filter(rent_count__gt=0)
            .order_by("-rent_count", "name")[:k]
        )

    return render(
        request,
        "taxi_rental_app/manager/report_top_clients.html",
        {"form": form, "clients_data": clients_data},
    )


@role_required(["manager"])
def manager_report_model_usage(request, current_user, current_role):
    """Report 5: Model usage counts"""
    model_data = (
        Model.objects.annotate(rent_count=Count("rents"))
        .select_related("car")
        .order_by("car__brand", "model_id")
    )

    return render(
        request,
        "taxi_rental_app/manager/report_model_usage.html",
        {"model_data": model_data},
    )


@role_required(["manager"])
def manager_report_driver_stats(request, current_user, current_role):
    """Report 6: Driver stats (rent count, average rating)"""
    driver_data = Driver.objects.annotate(
        total_rents=Count("rents", distinct=True),
        avg_rating=Avg("reviews_received__rating"),
    ).order_by("name")

    # Format avg_rating to 2 decimal places where it exists
    for driver in driver_data:
        if driver.avg_rating is not None:
            driver.avg_rating_formatted = "{:.2f}".format(driver.avg_rating)
        else:
            driver.avg_rating_formatted = "N/A"

    return render(
        request,
        "taxi_rental_app/manager/report_driver_stats.html",
        {"driver_data": driver_data},
    )


@role_required(["manager"])
def manager_report_cross_city(request, current_user, current_role):
    """Report 7: Clients from C1 who booked rents with drivers from C2"""
    clients_data = None
    form = CrossCityClientsForm(request.GET or None)
    if form.is_valid():
        city1 = form.cleaned_data["city1"]
        city2 = form.cleaned_data["city2"]

        # Find clients with at least one address in city1
        clients_in_city1 = Client.objects.filter(
            addresses__city__iexact=city1
        ).distinct()

        # Find drivers with an address in city2
        drivers_in_city2 = Driver.objects.filter(address__city__iexact=city2)

        # Find rents booked by clients_in_city1 involving drivers_in_city2
        relevant_rents = Rent.objects.filter(
            client__in=Subquery(clients_in_city1.values("email")),
            driver__in=Subquery(drivers_in_city2.values("name")),
        )

        # Get the distinct clients from these rents
        client_emails = relevant_rents.values_list(
            "client__email", flat=True
        ).distinct()
        clients_data = Client.objects.filter(email__in=client_emails).order_by("name")

    return render(
        request,
        "taxi_rental_app/manager/report_cross_city.html",
        {"form": form, "clients_data": clients_data},
    )


@role_required(["manager"])
def manager_report_problematic_drivers(request, current_user, current_role):
    """Report 8: Problematic drivers in Chicago (Group of 4)"""
    target_city = "Chicago"

    # 1. Drivers in Chicago with avg rating < 2.5
    drivers_query = (
        Driver.objects.filter(address__city__iexact=target_city)
        .annotate(
            avg_rating=Avg("reviews_received__rating"),
            rent_count=Count("rents"),  # Needed for later filter
        )
        .filter(avg_rating__lt=2.5)
    )

    # 2. Find rents for these drivers booked by clients with address in Chicago
    # Subquery for clients in Chicago
    chicago_clients = Client.objects.filter(
        addresses__city__iexact=target_city
    ).distinct()

    # Filter drivers based on rents from Chicago clients
    # This is complex: for each driver, check if they have >= 2 rents from distinct Chicago clients
    problematic_drivers = []
    for driver in drivers_query:
        rents_by_chicago_clients = Rent.objects.filter(
            driver=driver, client__in=Subquery(chicago_clients.values("email"))
        )
        # Check if there are at least 2 distinct clients among these rents
        distinct_clients_count = (
            rents_by_chicago_clients.values("client").distinct().count()
        )

        if distinct_clients_count >= 2:
            # Also ensure driver drove in at least two such rents (might be implied by distinct clients)
            if rents_by_chicago_clients.count() >= 2:
                # Format avg_rating
                driver.avg_rating_formatted = (
                    "{:.2f}".format(driver.avg_rating) if driver.avg_rating else "N/A"
                )
                problematic_drivers.append(driver)

    return render(
        request,
        "taxi_rental_app/manager/report_problematic_drivers.html",
        {"drivers": problematic_drivers, "target_city": target_city},
    )


@role_required(["manager"])
def manager_report_brand_summary(request, current_user, current_role):
    """Report 9: Brand summary (avg driver rating, rent count) (Group of 4)"""

    # Annotate Cars (Brands) with relevant statistics
    brand_data = (
        Car.objects.annotate(
            # Calculate average rating of drivers who can drive *any* model of this brand
            # This requires joining Car -> Model -> Drives -> Driver -> Review
            # Using Subquery or complex annotation might be needed. Let's try annotating Drivers first.
            avg_driver_rating_for_brand=Avg(
                # Find ratings of drivers associated with models of this car brand
                Review.objects.filter(
                    driver__drives_models__car=OuterRef(
                        "pk"
                    )  # Filter reviews based on drivers who drive models of the outer Car (brand)
                ).values(
                    "rating"
                )  # Get the rating values
                # Note: This calculates the average over *all* reviews for those drivers, not just reviews related to this brand's models.
                # A more precise (and complex) query might be needed if the requirement is stricter.
                # For demo, this gives an idea.
            ),
            # Count total rents using models of this brand
            total_rents_for_brand=Count(
                "models__rents"  # Count rents associated with models belonging to this car
            ),
        )
        .filter(
            # Optionally filter out brands with no models or no data
            total_rents_for_brand__gt=0
        )
        .order_by("brand")
    )

    # Format avg_rating
    for brand in brand_data:
        if brand.avg_driver_rating_for_brand is not None:
            brand.avg_driver_rating_formatted = "{:.2f}".format(
                brand.avg_driver_rating_for_brand
            )
        else:
            brand.avg_driver_rating_formatted = "N/A"

    return render(
        request,
        "taxi_rental_app/manager/report_brand_summary.html",
        {"brand_data": brand_data},
    )


# --- Driver Views ---


@role_required(["driver"])
def driver_dashboard(request, driver_name, current_user, current_role):
    driver = current_user  # Passed by decorator
    # Example stats for dashboard
    upcoming_rents = Rent.objects.filter(
        driver=driver, rent_date__gte=timezone.now().date()
    ).order_by("rent_date")
    avg_rating = driver.reviews_received.aggregate(Avg("rating"))["rating__avg"]
    avg_rating_formatted = "{:.2f}".format(avg_rating) if avg_rating else "N/A"

    context = {
        "driver": driver,
        "upcoming_rents": upcoming_rents,
        "avg_rating": avg_rating_formatted,
    }
    return render(request, "taxi_rental_app/driver/dashboard.html", context)


@role_required(["driver"])
def driver_model_list(request, driver_name, current_user, current_role):
    """Allows driver to see all models"""
    all_models = (
        Model.objects.select_related("car").all().order_by("car__brand", "model_id")
    )
    return render(
        request,
        "taxi_rental_app/driver/model_list.html",
        {"models": all_models, "driver": current_user},
    )


@role_required(["driver"])
@transaction.atomic
def driver_update_drives(request, driver_name, current_user, current_role):
    """Allows driver to declare which models they can drive"""
    driver = current_user
    if request.method == "POST":
        form = DrivesForm(request.POST)
        if form.is_valid():
            selected_models = form.cleaned_data["models"]
            # Clear existing certifications and add new ones
            driver.drives_models.clear()
            driver.drives_models.add(*selected_models)
            messages.success(request, "Your drivable models have been updated.")
            return redirect("taxi_rental_app:driver_dashboard", driver_name=driver.name)
    else:
        # Pre-populate form with currently selected models
        initial_models = driver.drives_models.all()
        form = DrivesForm(initial={"models": initial_models})

    return render(
        request,
        "taxi_rental_app/driver/drives_form.html",
        {"form": form, "driver": driver},
    )


@role_required(["driver"])
@transaction.atomic
def driver_update_address(request, driver_name, current_user, current_role):
    """Allows driver to update their address"""
    driver = current_user
    address = driver.address

    if request.method == "POST":
        form = DriverAddressForm(request.POST, instance=address)
        if form.is_valid():
            try:
                # Check if the new address already exists and is used by another driver
                new_addr_data = form.cleaned_data
                existing_address = (
                    Address.objects.filter(
                        road_name=new_addr_data["road_name"],
                        number=new_addr_data["number"],
                        city=new_addr_data["city"],
                    )
                    .exclude(pk=address.pk)
                    .first()
                )  # Exclude current address

                if existing_address and hasattr(existing_address, "driver_resident"):
                    messages.error(
                        request, "This address is already assigned to another driver."
                    )
                else:
                    form.save()
                    messages.success(request, "Your address has been updated.")
                    return redirect(
                        "taxi_rental_app:driver_dashboard", driver_name=driver.name
                    )
            except Exception as e:
                messages.error(request, f"An error occurred: {e}")

    else:
        form = DriverAddressForm(instance=address)
    return render(
        request,
        "taxi_rental_app/driver/address_form.html",
        {"form": form, "driver": driver},
    )


# --- Client Views ---


@role_required(["client"])
def client_dashboard(request, client_email, current_user, current_role):
    client = current_user
    recent_rents = client.rents.all().order_by("-rent_date")[:5]  # Show last 5 rents
    context = {
        "client": client,
        "recent_rents": recent_rents,
    }
    return render(request, "taxi_rental_app/client/dashboard.html", context)


@role_required(["client"])
def client_search_available(request, client_email, current_user, current_role):
    """Search for available models on a given date"""
    available_models = None
    form = RentSearchForm(request.GET or None)

    if form.is_valid():
        target_date = form.cleaned_data["rent_date"]

        # 1. Models NOT used in another rent on date D
        rented_models_on_date = Rent.objects.filter(rent_date=target_date).values_list(
            "model_id", flat=True
        )

        # 2. Drivers NOT driving on date D
        busy_drivers_on_date = Rent.objects.filter(rent_date=target_date).values_list(
            "driver_id", flat=True
        )

        # 3. Find models that meet criteria i, ii, iii
        # Start with all models, exclude rented ones, then check for available drivers who can drive them
        available_models = (
            Model.objects.exclude(pk__in=rented_models_on_date)  # Criterion i)
            .filter(
                # Criterion ii) & iii): Exists driver R who can drive model X (in Drives table) AND R is not busy
                drivers_certified__in=Driver.objects.exclude(
                    pk__in=busy_drivers_on_date
                )
            )
            .distinct()
            .select_related("car")
            .order_by("car__brand", "model_id")
        )

        # Pass the date and results to the booking form view
        return client_book_rent(
            request,
            client_email,
            available_models_qs=available_models,
            rent_date=target_date,
        )

    # If form is not valid or not submitted, show search form
    return render(
        request,
        "taxi_rental_app/client/book_rent_form.html",
        {"search_form": form, "client": current_user},
    )


@role_required(["client"])
@transaction.atomic
def client_book_rent(
    request,
    client_email,
    current_user,
    current_role,
    available_models_qs=None,
    rent_date=None,
):
    """Handles displaying the booking form (with available models) and processing the booking"""
    client = current_user

    if request.method == "POST":
        # Repopulate the queryset for the form validation
        form_rent_date = request.POST.get("rent_date")
        if not form_rent_date:
            messages.error(request, "Booking date is missing.")
            return redirect(
                "taxi_rental_app:client_search_available", client_email=client.email
            )

        # Re-calculate available models for validation
        rented_models_on_date = Rent.objects.filter(
            rent_date=form_rent_date
        ).values_list("model_id", flat=True)
        busy_drivers_on_date = Rent.objects.filter(
            rent_date=form_rent_date
        ).values_list(
            "driver__name", flat=True
        )  # Use driver name (PK)
        validation_qs = (
            Model.objects.exclude(pk__in=rented_models_on_date)
            .filter(
                drivers_certified__name__in=Driver.objects.exclude(
                    pk__in=busy_drivers_on_date
                ).values_list("name", flat=True)
            )
            .distinct()
        )

        form = BookRentForm(request.POST, available_models_qs=validation_qs)

        if form.is_valid():
            selected_model = form.cleaned_data["model"]
            use_best_driver = form.cleaned_data["use_best_driver"]
            target_date = form.cleaned_data["rent_date"]  # Get date from hidden field

            # Find available drivers for the selected model on that date
            available_drivers = Driver.objects.filter(
                drives_models=selected_model  # Can drive the selected model
            ).exclude(
                name__in=Rent.objects.filter(rent_date=target_date).values_list(
                    "driver__name", flat=True
                )  # Not busy on that date
            )

            assigned_driver = None
            if available_drivers.exists():
                if use_best_driver:
                    # Find best rated among available drivers (Group of 4)
                    assigned_driver = (
                        available_drivers.annotate(
                            avg_rating=Avg("reviews_received__rating")
                        )
                        .order_by("-avg_rating", "?")
                        .first()
                    )  # Order by rating desc, random tie-break
                else:
                    # Assign arbitrary available driver
                    assigned_driver = random.choice(list(available_drivers))

            if assigned_driver:
                # Create the rent record
                Rent.objects.create(
                    rent_date=target_date,
                    client=client,
                    driver=assigned_driver,
                    model=selected_model,
                )
                messages.success(
                    request,
                    f"Rent booked successfully for {target_date} with driver {assigned_driver.name} and model {selected_model}.",
                )
                return redirect(
                    "taxi_rental_app:client_rent_list", client_email=client.email
                )
            else:
                messages.error(
                    request,
                    f"Sorry, no drivers are available for {selected_model} on {target_date}. Please try another model or date.",
                )
                # Redirect back to search or show form again with error
                return redirect(
                    "taxi_rental_app:client_search_available", client_email=client.email
                )
        else:
            # Form is invalid (e.g., selected model became unavailable)
            messages.error(
                request,
                "Booking failed. The selected model might no longer be available. Please try searching again.",
            )
            # Need to pass the search form again if redirecting back to the initial search/book page
            search_form = RentSearchForm(
                initial={"rent_date": rent_date} if rent_date else None
            )
            return render(
                request,
                "taxi_rental_app/client/book_rent_form.html",
                {"search_form": search_form, "client": client},
            )

    # If GET request (coming from client_search_available)
    elif available_models_qs is not None and rent_date is not None:
        if available_models_qs.exists():
            book_form = BookRentForm(
                initial={"rent_date": rent_date},
                available_models_qs=available_models_qs,
            )
            return render(
                request,
                "taxi_rental_app/client/available_models.html",
                {"book_form": book_form, "rent_date": rent_date, "client": client},
            )
        else:
            messages.warning(
                request, f"No models available for booking on {rent_date}."
            )
            # Show search form again
            search_form = RentSearchForm(initial={"rent_date": rent_date})
            return render(
                request,
                "taxi_rental_app/client/book_rent_form.html",
                {"search_form": search_form, "client": client},
            )
    else:
        # Should not happen directly, redirect to search
        return redirect(
            "taxi_rental_app:client_search_available", client_email=client.email
        )


@role_required(["client"])
def client_rent_list(request, client_email, current_user, current_role):
    """Shows list of rents booked by the client"""
    client = current_user
    rents = client.rents.select_related("driver", "model", "model__car").order_by(
        "-rent_date"
    )

    # Check if client has rented from a driver to enable review link
    rented_driver_names = rents.values_list("driver__name", flat=True).distinct()

    return render(
        request,
        "taxi_rental_app/client/rent_list.html",
        {
            "client": client,
            "rents": rents,
            "rented_driver_names": list(
                rented_driver_names
            ),  # Pass list for template check
        },
    )


@role_required(["client"])
@transaction.atomic
def client_write_review(request, client_email, driver_name, current_user, current_role):
    """Allows client to review a driver they have rented from"""
    client = current_user
    driver = get_object_or_404(Driver, pk=driver_name)

    # Security Check: Verify the client has actually rented from this driver
    has_rented = Rent.objects.filter(client=client, driver=driver).exists()
    if not has_rented:
        messages.error(
            request, f"You can only review drivers you have previously rented."
        )
        return redirect("taxi_rental_app:client_rent_list", client_email=client.email)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.client = client
            review.driver = driver
            review.save()
            messages.success(
                request, f"Review for driver {driver.name} submitted successfully."
            )
            return redirect(
                "taxi_rental_app:client_rent_list", client_email=client.email
            )
    else:
        form = ReviewForm()

    return render(
        request,
        "taxi_rental_app/client/review_form.html",
        {"form": form, "client": client, "driver": driver},
    )


# --- Client Registration (Example) ---
@transaction.atomic
def register_client(request):
    if request.method == "POST":
        client_form = ClientForm(request.POST, prefix="client")
        address_form = AddressForm(request.POST, prefix="address")
        # We will handle the credit card details manually below,
        # primarily focusing on getting the card number from the POST request initially.

        # Validate client and address forms first
        if client_form.is_valid() and address_form.is_valid():
            try:
                # 1. Save Address first (using get_or_create to handle potential duplicates)
                address, address_created = Address.objects.get_or_create(
                    road_name=address_form.cleaned_data["road_name"],
                    number=address_form.cleaned_data["number"],
                    city=address_form.cleaned_data["city"],
                )

                # 2. Save Client (might raise IntegrityError if email exists)
                client = client_form.save()

                # 3. Link Client and Address via the through model
                ClientAddress.objects.create(client=client, address=address)

                # 4. Handle Credit Card Manually for Registration
                card_number_raw = request.POST.get(
                    "cc-card_number"
                )  # Get card number from POST

                # Validate card number format and uniqueness
                if not card_number_raw:
                    raise ValidationError("Credit card number is required.")

                card_validator = RegexValidator(
                    regex=r"^\d{16}$", message="Card number must be 16 digits."
                )
                try:
                    card_validator(card_number_raw)  # Validate format

                    # Check if card number already exists (Primary Key check)
                    if CreditCard.objects.filter(pk=card_number_raw).exists():
                        raise ValidationError(
                            "A credit card with this number already exists."
                        )

                    # Create the CreditCard object, explicitly assigning the payment address
                    cc = CreditCard(
                        card_number=card_number_raw,
                        payment_addr=address,  # Assign the address created/found earlier
                    )
                    # Perform model validation (checks, etc.) before saving
                    cc.full_clean(
                        exclude=["client"]
                    )  # Exclude client field as it's linked via ManyToMany later
                    cc.save()

                    # Add the card to the client's ManyToMany relationship
                    client.credit_cards.add(cc)

                    # If everything succeeded
                    messages.success(
                        request, f"Client '{client.name}' registered successfully!"
                    )
                    # Log them in (mock session)
                    set_user_role(request, "client", client.email)
                    return redirect(
                        "taxi_rental_app:client_dashboard", client_email=client.email
                    )

                except ValidationError as e:
                    # Handle card number validation errors (format, uniqueness, or model validation)
                    transaction.set_rollback(True)  # Rollback transaction on error
                    # Extract specific messages if possible
                    error_msg = "Invalid credit card details."
                    if hasattr(e, "message_dict"):
                        # Use Django's built-in form/model validation messages
                        error_msg = "; ".join(
                            [f"{k}: {v[0]}" for k, v in e.message_dict.items()]
                        )
                    elif hasattr(e, "message"):
                        error_msg = e.message
                    elif e.messages:
                        error_msg = "; ".join(e.messages)

                    messages.error(request, f"Registration failed: {error_msg}")
                    # Fall through to re-render the form with errors below

            except IntegrityError:
                # Handle potential duplicate client email
                messages.error(
                    request,
                    f"Registration failed. A client with email '{client_form.cleaned_data['email']}' might already exist.",
                )
                transaction.set_rollback(True)  # Rollback transaction
                # Fall through to re-render the form with errors below

            except Exception as e:
                # Catch any other unexpected errors during DB operations
                messages.error(
                    request, f"An unexpected error occurred during registration: {e}"
                )
                transaction.set_rollback(True)  # Rollback transaction
                # Fall through to re-render the form with errors below

        else:
            # Client form or Address form is invalid
            messages.error(
                request,
                "Please correct the errors in the account or address information.",
            )
            # Fall through to re-render the form with errors below

        # --- Re-render form if POST failed validation or encountered errors ---
        # We need to pass the forms back, including the cc_form for display consistency
        # (even though we didn't use its full validation for payment_addr)
        # Re-populate cc_form with POST data if available (excluding payment_addr logic)
        cc_form_data = request.POST.copy()
        cc_form_data.pop(
            "cc-payment_addr", None
        )  # Remove payment addr from data used for form
        cc_form = CreditCardForm(
            cc_form_data or None, prefix="cc", client_addresses=None
        )

        return render(
            request,
            "taxi_rental_app/registration/register_client.html",
            {
                "client_form": client_form,  # Contains errors if invalid
                "address_form": address_form,  # Contains errors if invalid
                "cc_form": cc_form,  # For display, might show card number error if format was wrong
            },
        )

    else:  # GET Request
        client_form = ClientForm(prefix="client")
        address_form = AddressForm(prefix="address")
        # Initialize with empty queryset for payment address, as no address exists yet
        cc_form = CreditCardForm(prefix="cc", client_addresses=None)

    return render(
        request,
        "taxi_rental_app/registration/register_client.html",
        {"client_form": client_form, "address_form": address_form, "cc_form": cc_form},
    )


# --- Context Processor ---
# Makes role/user available in all templates
def user_roles(request):
    role, user = get_user_role(request)
    return {
        "current_role": role,
        "current_user": user,
    }
