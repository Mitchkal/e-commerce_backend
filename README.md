# E-Commerce Backend

A robust Django backend API for an e-commerce platform, supporting customer and admin operations, secure payments, caching, and email notifications.

## Table of Contents

- [Features](#features)
- [User Stories](#user-stories)
  - [Customers](#customers)
  - [Admin](#admin)
- [Getting Started](#getting-started)
- [Models](#models)
- [API Endpoints](#api-endpoints)
- [Security](#security)
- [Payment Integration](#payment-integration)
- [Caching](#caching)
- [Emailing](#emailing)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- Built with Django and PostgreSQL
- User authentication & authorization (JWT for users, session for admins)
- Product catalog management with image storage on Cloudinary CDN
- Shopping cart & checkout flow
- Order processing, tracking, and status management
- Secure payment gateway integration via Paystack
- Inventory management
- Redis caching for products and customer profiles
- Email notifications (order confirmation, password reset, order shipped, etc.) via Celery tasks
- Admin dashboard endpoints
- Role-based access control
- RESTful API design
- Rate throttling for API endpoints
- Robust password policy using Django validators
- Product search & filtering (price, category, tags, description, featured)

---

## User Stories

### Customers

- As a customer, I can register and log in securely.
- As a customer, I can browse products and view details, including images.
- As a customer, I can add or remove products from my cart (authentication required).
- As a customer, I can checkout and create orders.
- As a customer, I can pay securely via Paystack and receive a checkout URL.
- As a customer, I receive email notifications for signup, payment, and when my order is shipped.
- As a customer, I can view my order history and track order status.
- As a customer, I can leave reviews on products.

### Admin

- As an admin, I can log in securely.
- As an admin, I can add, update, or remove products.
- As an admin, I can manage inventory and view stock levels.
- As an admin, I can view and manage customer orders.
- As an admin, I can manually update order status (processing, shipped, completed).
- As an admin, I receive notifications for low inventory and other events.
- As an admin, I can manage user accounts and permissions.

---

## Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/e-commerce_backend.git
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables in `.env`.
4. Apply migrations:
   ```bash
   python manage.py migrate
   ```
5. Start the server:
   ```bash
   python manage.py runserver
   ```
6. Start Celery worker for background tasks:
   ```bash
   celery -A <project_name> worker -l info
   ```

---

## Models

- **Customer**: User profile and authentication
- **Product**: Product details, images (Cloudinary), tags, categories
- **Cart**: Shopping cart per user
- **CartItem**: Items in a cart
- **Order**: Order details, status (pending, processing, shipped, completed)
- **OrderItem**: Items in an order
- **Payment**: Payment records and status
- **Review**: Customer reviews for products

---

## API Endpoints

- `/api/products` - Public product catalog (search/filter by price, category, tags, etc.)
- `/api/auth` - User registration & login
- `/api/cart` - Cart operations (add/remove, authenticated users only)
- `/api/checkout` - Initiate order creation (authenticated users)
- `/api/pay` - Initiate payment via Paystack, returns checkout URL
- `/api/paystack/webhook` - Payment verification and order status update
- `/api/orders` - View orders; staff can update order status
- `/api/admin` - Admin operations (product, inventory, user management)

---

## Security

- Passwords hashed with Django's default hasher
- JWT authentication for users, session authentication for admins
- Role-based access control
- Input validation & sanitization
- Rate throttling for anonymous and authenticated users
- Robust password policy (Django validators, confirmation required)
- HTTPS recommended for deployment

---

## Payment Integration

- Paystack integration for secure payments
- Backend calculates order total and initiates payment
- Returns Paystack checkout URL for user redirection
- Webhook verifies payment and updates order status to "processing"

---

## Caching

- Redis caching for product queries (15 minutes) and customer profiles
- Signals clear caches on product updates
- Improves response times and reduces database load

---

## Emailing

- Transactional emails sent via Celery tasks (signup, payment, order shipped)
- SMTP integration (e.g., SendGrid)
- Customizable email templates
- Signals trigger email notifications for key events

---

## Contributing

Pull requests are welcome. Please open an issue first to discuss changes.

---

## License

This project is licensed under the MIT License.
