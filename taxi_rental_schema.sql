/* ============================================================
 Taxi‑Rental Management – Phase 2  | Relational Schema
 Target DBMS : PostgreSQL
 Authors      : Jeremiah B., Ele B., Matthew J., Maryann O.
 ============================================================ */
/* ---------- 0. CLEAN SLATE (optional) ----------- */
DO $$ BEGIN IF EXISTS (
    SELECT 1
    FROM pg_type
    WHERE typname = 'transmission_t'
) THEN DROP TYPE transmission_t;
END IF;
END $$;
DROP TABLE IF EXISTS Review,
Rent,
Drives,
Driver,
Model,
Car,
CreditCard,
Client_Address,
Address,
Client,
Manager CASCADE;
/* ---------- 1. DOMAIN‑LIKE ENUMS & COMMON TYPES ------------ */
CREATE TYPE transmission_t AS ENUM ('manual', 'automatic');
/* ---------- 2. MANAGER -------- */
CREATE TABLE Manager (
    ssn CHAR(11) PRIMARY KEY,
    -- Format: 123-45-6789
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    CHECK (ssn ~ '^\d{3}-\d{2}-\d{4}$')
);
COMMENT ON TABLE Manager IS 'Fleet administrator – logs in with SSN. Standalone entity.';
/* ---------- 3. CLIENT & CONTACT ---------------------------- */
CREATE TABLE Client (
    email VARCHAR(120) PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);
COMMENT ON TABLE Client IS 'End‑user who books rentals. Logs in with email.';
CREATE TABLE Address (
    address_id SERIAL PRIMARY KEY,
    road_name VARCHAR(120) NOT NULL,
    number VARCHAR(20) NOT NULL,
    city VARCHAR(80) NOT NULL
);
COMMENT ON TABLE Address IS 'Reusable address component for clients, drivers, and cards.';
/* Junction table: Client can have multiple addresses (1:N, requires at least one) */
CREATE TABLE Client_Address (
    client_email VARCHAR(120) NOT NULL REFERENCES Client(email) ON DELETE CASCADE,
    address_id INTEGER NOT NULL REFERENCES Address(address_id) ON DELETE CASCADE,
    PRIMARY KEY (client_email, address_id)
);
COMMENT ON TABLE Client_Address IS 'Links clients to their addresses (M:N conceptually, but 1:N from Client perspective).';
CREATE TABLE CreditCard (
    card_number CHAR(16) PRIMARY KEY,
    -- Expecting 16 digits
    client_email VARCHAR(120) NOT NULL REFERENCES Client(email) ON DELETE CASCADE,
    payment_addr INTEGER NOT NULL REFERENCES Address(address_id) ON DELETE RESTRICT,
    -- Each card MUST have a payment address
    CHECK (card_number ~ '^\d{16}$')
);
COMMENT ON TABLE CreditCard IS 'Client payment methods. Each tied to one client and one payment address.';
/* ---------- 4. CAR & MODEL --------------------------------- */
CREATE TABLE Car (
    car_id SERIAL PRIMARY KEY,
    brand VARCHAR(80) NOT NULL
);
COMMENT ON TABLE Car IS 'Represents the car brand.';
-- Model is a weak entity dependent on Car
CREATE TABLE Model (
    car_id INTEGER NOT NULL REFERENCES Car(car_id) ON DELETE CASCADE,
    model_id INTEGER NOT NULL,
    -- Partial key, unique within a car_id
    color VARCHAR(40) NOT NULL,
    construction_year SMALLINT NOT NULL CHECK (
        construction_year BETWEEN 1900 AND EXTRACT(
            YEAR
            FROM CURRENT_DATE
        ) + 1
    ),
    transmission transmission_t NOT NULL,
    PRIMARY KEY (car_id, model_id) -- Composite primary key for the weak entity
);
COMMENT ON TABLE Model IS 'Specific car model (weak entity w.r.t Car). Identified by (car_id, model_id).';
/* ---------- 5. DRIVER & QUALIFICATION ---------------------- */
CREATE TABLE Driver (
    name VARCHAR(100) PRIMARY KEY,
    -- Natural key, unique, used for login
    address_id INTEGER NOT NULL UNIQUE REFERENCES Address(address_id) ON DELETE RESTRICT -- Each driver has exactly one unique address
);
COMMENT ON TABLE Driver IS 'Chauffeur – logs in with unique name. Has exactly one address.';
-- Junction table: Which models a driver is certified for (M:N)
CREATE TABLE Drives (
    driver_name VARCHAR(100) NOT NULL REFERENCES Driver(name) ON DELETE CASCADE,
    car_id INTEGER NOT NULL,
    model_id INTEGER NOT NULL,
    PRIMARY KEY (driver_name, car_id, model_id),
    FOREIGN KEY (car_id, model_id) REFERENCES Model(car_id, model_id) ON DELETE CASCADE
);
COMMENT ON TABLE Drives IS 'Links drivers to the car models they are certified to drive (M:N relationship).';
/* ---------- 6. RENTAL -------------------------------------- */
CREATE TABLE Rent (
    rent_id SERIAL PRIMARY KEY,
    rent_date DATE NOT NULL,
    client_email VARCHAR(120) NOT NULL REFERENCES Client(email) ON DELETE RESTRICT,
    -- Can't delete client if they have rents
    driver_name VARCHAR(100) NOT NULL REFERENCES Driver(name) ON DELETE RESTRICT,
    -- Can't delete driver if they have rents
    car_id INTEGER NOT NULL,
    model_id INTEGER NOT NULL,
    FOREIGN KEY (car_id, model_id) REFERENCES Model(car_id, model_id) ON DELETE RESTRICT -- Can't delete model if used in rents
);
COMMENT ON TABLE Rent IS 'A one‑day booking connecting a client, driver, and car model for a specific date.';
/* ---------- 7. REVIEW (Weak entity Driver) ----------- */
-- Review identified by driver (weak entity), uses driver_name in PK
CREATE TABLE Review (
    driver_name VARCHAR(100) NOT NULL REFERENCES Driver(name) ON DELETE CASCADE,
    review_id SERIAL NOT NULL,
    -- Partial key, unique within a driver_name
    client_email VARCHAR(120) NOT NULL REFERENCES Client(email) ON DELETE CASCADE,
    -- Who wrote the review
    rating INTEGER NOT NULL CHECK (
        rating BETWEEN 0 AND 5
    ),
    message TEXT,
    PRIMARY KEY (driver_name, review_id),
    -- Composite primary key for weak entity
    UNIQUE (client_email, driver_name, review_id) -- Allow multiple reviews from one client *to* one driver (if needed, adjust if only one review ever allowed)
    -- If only ONE review per client per driver is allowed EVER, use: UNIQUE (client_email, driver_name)
);
COMMENT ON TABLE Review IS 'Client feedback on a driver (weak entity Driver). Identified by (driver_name, review_id).';
/* ---------- 8. PERFORMANCE INDEXES (Optional) --- */
CREATE INDEX idx_rent_date ON Rent(rent_date);
CREATE INDEX idx_review_driver ON Review(driver_name);
CREATE INDEX idx_review_client ON Review(client_email);
CREATE INDEX idx_drives_driver ON Drives(driver_name);
CREATE INDEX idx_drives_model ON Drives(car_id, model_id);
CREATE INDEX idx_client_addr_client ON Client_Address(client_email);
CREATE INDEX idx_client_addr_addr ON Client_Address(address_id);
CREATE INDEX idx_creditcard_client ON CreditCard(client_email);
CREATE INDEX idx_model_car ON Model(car_id);
/* ============================================================
 End of schema.
 ============================================================ */