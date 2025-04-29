# Taxi Rental Management Application (Phase 3)

Django application implementing the requirements for the college course project.

**Members:** Jeremiah B., Ele B., Matthew J., Maryann O.

## Setup Instructions

1.  **Prerequisites:**

    - Python 3.9+
    - PostgreSQL server running
    - `git` (optional, for cloning)

2.  **Clone the Repository (Optional):**

    ```bash
    git clon https://github.com/juebenjamin/taxi-rental-project.git
    cd taxi_rental_project
    ```

    Alternatively, download and extract the project files.

3.  **Create Virtual Environment:**

    ```bash
    python -m venv venv
    # Activate:
    # Windows: venv\Scripts\activate
    # macOS/Linux: source venv/bin/activate
    ```

4.  **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

5.  **Database Setup:**

    - Ensure your PostgreSQL server is running.
    - Create a database (e.g., `taxi_rental`).
    - Create a database user/role with privileges on the database (e.g., `taxi_user` with password `password`).
    - Create a `.env` file in the project root (`taxi_rental_project/`) with your database connection string:
      ```.env
      DATABASE_URL=postgres://taxi_user:password@localhost:5432/taxi_rental
      DJANGO_SECRET_KEY=your-very-secret-key-here # Generate a strong secret key
      DJANGO_DEBUG=True # Set to False in production
      # DJANGO_ALLOWED_HOSTS=yourdomain.com,localhost # Adjust for deployment
      ```
    - Apply the database schema:
      ```bash
      # Make sure you are in the project root directory (where manage.py is)
      # Replace 'taxi_user', 'taxi_rental' with your actual user/db if different
      psql -U taxi_user -d taxi_rental -f taxi_rental_schema_rev.sql
      ```
      _(Note: Django migrations are not used here as the schema is provided externally)_

6.  **Run the Development Server:**

    ```bash
    python manage.py runserver
    ```

7.  **Access the Application:**
    Open your web browser and go to `http://127.0.0.1:8000/`

## Demo Notes

- **Authentication:** Full user authentication (sign up/password management) is not implemented. Use the "Login / Select Role" page (`/login/`) to choose a role (Manager, Client, Driver) and enter a valid identifier (SSN, Email, Name) from the database to simulate being logged in. Sample identifiers are listed on the login page if data exists.
- **Data:** The application starts with an empty database defined by `taxi_rental_schema_rev.sql`. You will need to:
  - Manually add a Manager via SQL or the Django admin (if enabled).
  - Use the application to register Clients (or add via SQL/admin).
  - Use the Manager interface to add Drivers, Cars, and Models.
  - (Optional) Create a `seed_data.py` script using Django's shell or management commands to populate initial data for easier demoing.

## Key Features Implemented

- **Manager:** CRUD for Drivers, Cars, Models. All 9 reports (including group-of-4).
- **Driver:** Update address, view all models, declare drivable models.
- **Client:** Register (basic for demo), search available models, book rent (arbitrary or best driver), view rents, write reviews (with check).
- **Modern UI:** Uses Bootstrap 5 for styling.
