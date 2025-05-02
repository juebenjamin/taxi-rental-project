from django.urls import path
from . import views

# Using namespaces is good practice if you have multiple apps
app_name = "taxi_rental_app"

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.mock_login, name="login"),  # Mock login/role selection
    path("logout/", views.mock_logout, name="logout"),  # Mock logout
    # Manager URLs
    path("manager/", views.manager_dashboard, name="manager_dashboard"),
    path("manager/cars/", views.manager_car_list, name="manager_car_list"),
    path("manager/cars/add/", views.manager_car_create, name="manager_car_create"),
    path(
        "manager/cars/<int:pk>/edit/",
        views.manager_car_update,
        name="manager_car_update",
    ),
    path(
        "manager/cars/<int:pk>/delete/",
        views.manager_car_delete,
        name="manager_car_delete",
    ),
    path("manager/models/", views.manager_model_list, name="manager_model_list"),
    path(
        "manager/models/add/", views.manager_model_create, name="manager_model_create"
    ),
    # PK for model is composite (car_id, model_id), need custom URL or different approach
    # Using car_pk and model_pk for simplicity here
    path(
        "manager/models/<int:car_pk>/<int:model_pk>/edit/",
        views.manager_model_update,
        name="manager_model_update",
    ),
    path(
        "manager/models/<int:car_pk>/<int:model_pk>/delete/",
        views.manager_model_delete,
        name="manager_model_delete",
    ),
    path("manager/drivers/", views.manager_driver_list, name="manager_driver_list"),
    path(
        "manager/drivers/add/",
        views.manager_driver_create,
        name="manager_driver_create",
    ),
    path(
        "manager/drivers/<str:pk>/edit/",
        views.manager_driver_update,
        name="manager_driver_update",
    ),  # PK is name (str)
    path(
        "manager/drivers/<str:pk>/delete/",
        views.manager_driver_delete,
        name="manager_driver_delete",
    ),
    # Reports
    path(
        "manager/reports/top-clients/",
        views.manager_report_top_clients,
        name="manager_report_top_clients",
    ),
    path(
        "manager/reports/model-usage/",
        views.manager_report_model_usage,
        name="manager_report_model_usage",
    ),
    path(
        "manager/reports/driver-stats/",
        views.manager_report_driver_stats,
        name="manager_report_driver_stats",
    ),
    path(
        "manager/reports/cross-city/",
        views.manager_report_cross_city,
        name="manager_report_cross_city",
    ),
    path(
        "manager/reports/problematic-drivers/",
        views.manager_report_problematic_drivers,
        name="manager_report_problematic_drivers",
    ),
    path(
        "manager/reports/brand-summary/",
        views.manager_report_brand_summary,
        name="manager_report_brand_summary",
    ),
    # Driver URLs
    path("driver/<str:driver_name>/", views.driver_dashboard, name="driver_dashboard"),
    path(
        "driver/<str:driver_name>/models/",
        views.driver_model_list,
        name="driver_model_list",
    ),
    path(
        "driver/<str:driver_name>/drives/",
        views.driver_update_drives,
        name="driver_update_drives",
    ),
    path(
        "driver/<str:driver_name>/address/",
        views.driver_update_address,
        name="driver_update_address",
    ),
    # Client URLs
    path("client/<str:client_email>/", views.client_dashboard, name="client_dashboard"),
    path(
        "client/<str:client_email>/book/",
        views.client_search_available,
        name="client_search_available",
    ),
    path(
        "client/<str:client_email>/book/results/",
        views.client_book_rent,
        name="client_book_rent",
    ),  # POST target for booking
    path(
        "client/<str:client_email>/rents/",
        views.client_rent_list,
        name="client_rent_list",
    ),
    path(
        "client/<str:client_email>/review/<str:driver_name>/",
        views.client_write_review,
        name="client_write_review",
    ),
    # Add URLs for client registration, adding addresses/cards if implementing full registration
    path(
        "register/client/", views.register_client, name="register_client"
    ),  # Registration URL
]
