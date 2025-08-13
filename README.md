# ShopSite E-Commerce Backend API

A robust Django REST API backend for an e-commerce platform, supporting comprehensive customer and admin operations, secure payments via Paystack, Redis caching, and automated email notifications.

## Table of Contents

- [Features](#features)
- [User Stories](#user-stories)
  - [Customers](#customers)
  - [Admin](#admin)
- [Getting Started](#getting-started)
- [Models](#models)
- [API Endpoints](#api-endpoints)
  - [Authentication](#authentication)
  - [Products](#products)
  - [Cart Management](#cart-management)
  - [Orders](#orders)
  - [Payments](#payments)
  - [Reviews](#reviews)
  - [Admin Operations](#admin-operations)
- [Security](#security)
- [Payment Integration](#payment-integration)
- [Caching](#caching)
- [Email Notifications](#email-notifications)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **Framework**: Built with Django REST Framework and PostgreSQL
- **Authentication**: Dual authentication system (JWT for users, session for admins)
- **Product Management**: Complete catalog with image storage on Cloudinary CDN
- **Shopping Experience**: Full cart and checkout flow with inventory tracking
- **Order Processing**: Comprehensive order management with status tracking
- **Payment Integration**: Secure payment gateway via Paystack with webhook verification
- **Performance**: Redis caching for products and customer profiles (15-minute cache)
- **Notifications**: Automated email system using Celery for background tasks
- **Admin Dashboard**: Complete administrative interface with role-based access
- **API Features**: RESTful design, pagination, filtering, search, and rate limiting
- **Security**: Robust password policies and input validation

---

## User Stories

### Customers

- **Authentication**: Secure registration and login with JWT tokens
- **Product Browsing**: Browse products with advanced filtering (category, price, tags, description)
- **Shopping Cart**: Add/remove products, manage quantities (authentication required)
- **Checkout Process**: Create orders with shipping and billing addresses
- **Secure Payments**: Pay via Paystack integration with checkout URL redirection
- **Email Notifications**: Receive emails for signup, payment confirmations, and shipping updates
- **Order Tracking**: View order history and track current order status
- **Product Reviews**: Leave ratings and comments on purchased products
- **Profile Management**: Update personal information and preferences

### Admin

- **Secure Access**: Admin-specific authentication with session management
- **Product Management**: Complete CRUD operations for product catalog
- **Inventory Control**: Real-time stock management and low inventory alerts
- **Order Management**: View, process, and update order statuses
- **Customer Management**: Full customer account administration
- **Payment Oversight**: Monitor payment transactions and status
- **Review Moderation**: Manage customer reviews and ratings
- **System Analytics**: Access to comprehensive order and customer data

---

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL
- Redis
- Docker (optional)

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/yourusername/e-commerce_backend.git
   cd e-commerce_backend
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Environment setup:**
   Configure environment variables in `.env`:

   ```bash
   DATABASE_URL=postgresql://user:password@localhost:5432/shopsite
   REDIS_URL=redis://localhost:6379
   PAYSTACK_SECRET_KEY=your_paystack_secret_key
   CLOUDINARY_URL=your_cloudinary_url
   EMAIL_HOST_USER=your_email
   EMAIL_HOST_PASSWORD=your_email_password
   ```

4. **Database setup:**

   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   python manage.py seed_products
   ```

5. **Start services:**

   ```bash
   # Start Django server
   python manage.py runserver
   ```

### Docker Setup (Alternative)

```bash
# Build and start all services
# docker-compose build
docker-compose up -d
```

---

## Models

### Core Models

- **Customer**: Extended user model with profile information (UUID primary key)
- **Product**: Product catalog with images, categories, and inventory (UUID primary key)
- **Cart**: User shopping carts (UUID primary key)
- **CartItem**: Individual items in carts with quantities
- **Order**: Order records with status tracking (UUID primary key)
- **OrderItem**: Line items within orders
- **Payment**: Payment transaction records with Paystack integration
- **Review**: Customer product reviews and ratings (UUID primary key)

### Model Relationships

- Customer → Cart (One-to-One)
- Cart → CartItem (One-to-Many)
- Customer → Order (One-to-Many)
- Order → OrderItem (One-to-Many)
- Product → CartItem/OrderItem (One-to-Many)
- Order → Payment (One-to-One)
- Product → Review (One-to-Many)
- Customer → Review (One-to-Many)

---

## API Endpoints

### Authentication

| Endpoint              | Method | Description                              | Authentication |
| --------------------- | ------ | ---------------------------------------- | -------------- |
| `/api/signup/`        | POST   | Customer registration with welcome email | None           |
| `/api/token/`         | POST   | JWT token generation (login)             | None           |
| `/api/token/refresh/` | POST   | Refresh JWT access token                 | None           |

**Registration Request:**

```json
{
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890",
  "date_of_birth": "1990-01-01",
  "password": "securepassword123",
  "confirm_password": "securepassword123"
}
```

### Products

| Endpoint                               | Method    | Description                             | Authentication |
| -------------------------------------- | --------- | --------------------------------------- | -------------- |
| `/api/products/`                       | GET       | List products with filtering and search | None           |
| `/api/products/`                       | POST      | Create new product                      | JWT (Staff)    |
| `/api/products/{id}/`                  | GET       | Product detail view                     | None           |
| `/api/products/{id}/`                  | PUT/PATCH | Update product                          | JWT (Staff)    |
| `/api/products/{id}/`                  | DELETE    | Delete product                          | JWT (Staff)    |
| `/api/products/{id}/add_to_cart/`      | POST      | Add product to cart                     | JWT            |
| `/api/products/{id}/remove_from_cart/` | DELETE    | Remove from cart                        | JWT            |

**Product Filtering Options:**

- `category`: Filter by product category
- `price`, `price__gt`, `price__lt`: Price range filtering
- `tags`, `tags__icontains`: Tag-based filtering
- `description__icontains`: Search in descriptions
- `is_featured`: Featured products only
- `is_in_stock`: Available products only
- `page`, `page_size`: Pagination controls

### Cart Management

| Endpoint                | Method               | Description                    | Authentication |
| ----------------------- | -------------------- | ------------------------------ | -------------- |
| `/api/cart/`            | GET                  | List user's carts              | JWT            |
| `/api/cart/me/`         | GET                  | Get current user's active cart | JWT            |
| `/api/cart/{id}/`       | GET/PUT/PATCH/DELETE | Cart operations                | JWT            |
| `/api/cart-items/`      | GET/POST             | Cart item operations           | JWT            |
| `/api/cart-items/{id}/` | GET/PUT/PATCH/DELETE | Individual cart item           | JWT            |

### Orders

| Endpoint                              | Method | Description            | Authentication |
| ------------------------------------- | ------ | ---------------------- | -------------- |
| `/api/checkout/`                      | POST   | Create order from cart | JWT            |
| `/api/orders/`                        | GET    | List user orders       | JWT            |
| `/api/orders/{id}/`                   | GET    | Order details          | JWT            |
| `/api/orders/{id}/cancel/`            | POST   | Cancel order           | JWT            |
| `/api/orders/{id}/mark_as_shipped/`   | POST   | Mark as shipped        | JWT (Admin)    |
| `/api/orders/{id}/mark_as_completed/` | POST   | Mark as completed      | JWT (Admin)    |

**Checkout Request:**

```json
{
  "shipping_address": "123 Main St, City, State 12345",
  "billing_address": "456 Billing Ave, City, State 12345"
}
```

**Order Status Values:**

- `PENDING`: Awaiting payment
- `CREATED`: Order created, payment pending
- `PROCESSING`: Payment confirmed, preparing shipment
- `SHIPPED`: Order dispatched
- `COMPLETED`: Order delivered
- `CANCELLED`: Order cancelled
- `REFUNDED`: Payment refunded

### Payments

| Endpoint             | Method | Description               | Authentication |
| -------------------- | ------ | ------------------------- | -------------- |
| `/api/pay/`          | POST   | Initiate Paystack payment | JWT            |
| `/api/payment/`      | GET    | List user payments        | JWT            |
| `/api/payment/{id}/` | GET    | Payment details           | JWT            |

**Payment Request:**

```json
{
  "order_id": 123
}
```

**Payment Response:**

```json
{
  "status": "success",
  "message": "Authorization URL created",
  "data": {
    "authorization_url": "https://checkout.paystack.com/...",
    "access_code": "...",
    "reference": "..."
  }
}
```

### Reviews

| Endpoint             | Method               | Description         | Authentication |
| -------------------- | -------------------- | ------------------- | -------------- |
| `/api/reviews/`      | GET/POST             | List/create reviews | JWT            |
| `/api/reviews/{id}/` | GET/PUT/PATCH/DELETE | Review operations   | JWT            |

**Review Request:**

```json
{
  "product": "product-uuid",
  "rating": 5,
  "comment": "Excellent product, highly recommend!"
}
```

### Admin Operations

| Endpoint                     | Method               | Description         | Authentication |
| ---------------------------- | -------------------- | ------------------- | -------------- |
| `/api/admin/customers/`      | GET/POST             | Customer management | JWT (Admin)    |
| `/api/admin/customers/{id}/` | GET/PUT/PATCH/DELETE | Individual customer | JWT (Admin)    |

### User Profile

| Endpoint                    | Method        | Description             | Authentication |
| --------------------------- | ------------- | ----------------------- | -------------- |
| `/api/customer_profile/me/` | GET/PUT/PATCH | User profile management | JWT            |

---

## Security

### Authentication & Authorization

- **JWT Tokens**: Secure user authentication with access/refresh token system
- **Session Authentication**: Admin interface uses Django sessions
- **Role-based Access**: Staff-only endpoints for administrative functions
- **Password Security**: Django's robust password validation and hashing

### Data Protection

- **Input Validation**: Comprehensive request validation using DRF serializers
- **Rate Limiting**: API rate limiting for anonymous and authenticated users
- **UUID Primary Keys**: Enhanced security using UUID instead of sequential IDs
- **HTTPS Ready**: Designed for HTTPS deployment

### Security Headers

- CORS configuration
- CSRF protection
- Secure password policies with confirmation requirements

---

## Payment Integration

### Paystack Integration

- **Secure Processing**: All payments handled through Paystack's secure infrastructure
- **Webhook Verification**: Automatic payment verification via Paystack webhooks
- **Order Updates**: Automatic order status updates upon successful payment
- **Multiple Payment Methods**: Support for cards, bank transfers, and mobile money

### Payment Flow

1. Customer initiates payment via `/api/pay/`
2. Backend calculates order total and creates Paystack transaction
3. Customer redirected to Paystack checkout URL
4. Payment processed securely by Paystack
5. Webhook confirms payment and updates order status to "PROCESSING"
6. Customer receives payment confirmation email

---

## Caching

### Redis Implementation

- **Product Caching**: Product queries cached for 15 minutes
- **Customer Profile Caching**: User profile data cached for performance
- **Cache Invalidation**: Automatic cache clearing on product updates via Django signals
- **Performance Benefits**: Reduced database load and improved response times

### Cache Keys

```python
# Product list cache
f"products:list:{hash(query_params)}"

# Product detail cache
f"product:detail:{product_id}"

# Customer profile cache
f"customer:profile:{customer_id}"
```

---

## Email Notifications

### Celery Task Queue

- **Background Processing**: All emails sent asynchronously via Celery
- **SMTP Integration**: Compatible with SendGrid, Gmail, and other SMTP providers
- **Template System**: Customizable HTML email templates

### Email Types

- **Welcome Email**: Sent upon customer registration
- **Order Confirmation**: Sent when order is created
- **Payment Confirmation**: Sent after successful payment
- **Shipping Notification**: Sent when order status changes to "SHIPPED"
- **Admin Alerts**: Low inventory and other administrative notifications

### Configuration

```python
# settings.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
```

---

## API Documentation

### OpenAPI 3.0 Specification

- **Interactive Documentation**: Available via Swagger UI
- **Complete Schema**: All endpoints, request/response formats documented
- **Authentication Examples**: JWT and session authentication examples
- **Model Schemas**: Detailed model field descriptions

### Response Formats

**Success Response:**

```json
{
  "count": 25,
  "next": "http://api.example.com/api/products/?page=2",
  "previous": null,
  "results": [...]
}
```

**Error Response:**

```json
{
  "error": "Validation failed",
  "details": {
    "email": ["This field is required."],
    "password": ["Password must be at least 8 characters."]
  }
}
```

### Rate Limiting

- **Anonymous Users**: 100 requests/hour
- **Authenticated Users**: 1000 requests/hour
- **Admin Users**: 5000 requests/hour

---

## Development & Testing

### Code Quality

- **PEP 8 Compliance**: Python code follows PEP 8 standards
- **Django Best Practices**: Following Django and DRF conventions
- **Error Handling**: Comprehensive error handling and logging
- **API Versioning**: Prepared for future API versioning

### Testing

```bash
# Run all tests
python manage.py test

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

### Development Tools

- **Django Debug Toolbar**: Available in development
- **API Documentation**: Auto-generated from code
- **Database Migrations**: Proper migration management
- **Environment Configuration**: Separate settings for dev/prod

---

## Deployment

### Production Considerations

- **Database**: PostgreSQL with connection pooling
- **Cache**: Redis cluster for high availability
- **Static Files**: Cloudinary CDN for media files
- **Email**: Production SMTP service (SendGrid recommended)
- **Monitoring**: Application and database monitoring setup
- **Backup**: Automated database backup strategy

### Environment Variables

```bash
# Production settings
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
SECRET_KEY=your-secret-key
PAYSTACK_SECRET_KEY=sk_live_...
CLOUDINARY_URL=cloudinary://...
```

---

## Contributing

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following coding standards
4. Add tests for new functionality
5. Run tests and ensure they pass
6. Commit changes (`git commit -m 'Add amazing feature'`)
7. Push to branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Pull Request Guidelines

- Include detailed description of changes
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass
- Follow existing code style

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Support

For support and questions:

- **Documentation**: Check this README and API documentation
- **Issues**: Open GitHub issues for bugs and feature requests
- **Email**: Contact the development team

---

## Changelog

### Version 1.0.0

- Initial release with core e-commerce functionality
- JWT authentication system
- Paystack payment integration
- Redis caching implementation
- Email notification system
- Comprehensive API documentation
