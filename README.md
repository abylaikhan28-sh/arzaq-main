# Arzaq Backend API

Production-ready FastAPI backend for the Arzaq Food-Tech Platform - Fighting Food Waste by connecting restaurants with customers for discounted unsold meals.

## Features

- **FastAPI** - Modern, fast web framework
- **PostgreSQL** - Robust relational database
- **SQLAlchemy** - Powerful ORM
- **JWT Authentication** - Secure token-based auth
- **Cloudinary** - Image upload and optimization
- **Alembic** - Database migrations
- **Role-based Access Control** - Client, Restaurant, Admin roles
- **Automatic API Documentation** - Interactive Swagger/ReDoc docs

## Tech Stack

- Python 3.9+
- FastAPI
- PostgreSQL 14+
- SQLAlchemy 2.0
- Alembic
- Cloudinary
- JWT (python-jose)
- Bcrypt (passlib)

---

## Setup Instructions for macOS

### Prerequisites

1. **Homebrew** (if not installed):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

2. **Python 3.9+**:
```bash
brew install python@3.11
python3 --version  # Verify installation
```

3. **PostgreSQL 14+**:
```bash
brew install postgresql@14
brew services start postgresql@14

# Check if PostgreSQL is running
psql postgres
```

---

### Step 1: Clone and Navigate

```bash
cd /Users/mac/Downloads/Arzaq-project/arzaq-backend
```

---

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# You should see (venv) in your terminal prompt
```

---

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### Step 4: Create PostgreSQL Database

```bash
# Connect to PostgreSQL
psql postgres

# Inside psql, run these commands:
CREATE DATABASE arzaq_db;
CREATE USER arzaq_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE arzaq_db TO arzaq_user;

# Exit psql
\q
```

---

### Step 5: Setup Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your favorite editor
nano .env  # or use: code .env
```

**Update `.env` with your configuration:**

```env
# Database
DATABASE_URL=postgresql://arzaq_user:your_secure_password@localhost:5432/arzaq_db

# JWT Secret (generate with: openssl rand -hex 32)
SECRET_KEY=your-generated-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# CORS Origins
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000,https://arzaqmeal.vercel.app

# Cloudinary (get from https://cloudinary.com)
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# Server
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development
```

**Generate JWT Secret:**
```bash
openssl rand -hex 32
```

---

### Step 6: Run Database Migrations

```bash
# Initialize Alembic (only if not already initialized)
alembic init alembic  # Skip if alembic folder exists

# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

---

### Step 7: Create Admin User (Optional)

Create a Python script to add admin user:

```bash
# Create a file: create_admin.py
cat > create_admin.py << 'EOF'
from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine
from app.models.user import User, UserRole
from app.core.security import get_password_hash
from app.db.base import Base

# Create tables
Base.metadata.create_all(bind=engine)

# Create admin user
db = SessionLocal()

admin = User(
    email="admin@arzaq.kz",
    full_name="Admin User",
    hashed_password=get_password_hash("admin123"),
    role=UserRole.ADMIN,
    is_active=True,
    is_verified=True
)

db.add(admin)
db.commit()
print("Admin user created: admin@arzaq.kz / admin123")
db.close()
EOF

# Run the script
python create_admin.py
```

---

### Step 8: Run the Server

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use Python directly
python -m app.main
```

Server will start at: **http://localhost:8000**

---

## Access Documentation

Once the server is running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

---

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login with credentials
- `GET /api/auth/me` - Get current user info

### Foods
- `GET /api/foods` - Get all available foods
- `POST /api/foods` - Create food item (restaurant only)
- `GET /api/foods/me` - Get my food items
- `PUT /api/foods/{id}` - Update food item
- `DELETE /api/foods/{id}` - Delete food item
- `POST /api/foods/upload-image` - Upload food image

### Restaurants
- `GET /api/restaurants` - Get all restaurants
- `POST /api/restaurants` - Create restaurant
- `GET /api/restaurants/me` - Get my restaurant
- `POST /api/restaurants/{id}/approve` - Approve restaurant (admin)
- `POST /api/restaurants/{id}/reject` - Reject restaurant (admin)

### Orders
- `GET /api/orders` - Get orders (role-based)
- `POST /api/orders` - Create new order
- `PATCH /api/orders/{id}/status` - Update order status
- `GET /api/orders/impact/stats` - Get impact statistics

### Community Posts
- `GET /api/posts` - Get all posts
- `POST /api/posts` - Create post
- `POST /api/posts/{id}/like` - Toggle like
- `POST /api/posts/{id}/comments` - Add comment
- `DELETE /api/posts/{id}/comments/{comment_id}` - Delete comment

---

## Testing the API

### Using curl:

```bash
# Register a customer
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@test.com",
    "password": "test123",
    "full_name": "Test Customer",
    "role": "client"
  }'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -F "username=customer@test.com" \
  -F "password=test123"

# Get current user (use token from login)
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## Project Structure

```
arzaq-backend/
├── alembic/                 # Database migrations
│   ├── versions/
│   └── env.py
├── app/
│   ├── api/
│   │   └── routes/         # API endpoints
│   │       ├── auth.py
│   │       ├── foods.py
│   │       ├── restaurants.py
│   │       ├── orders.py
│   │       └── posts.py
│   ├── core/               # Core configuration
│   │   ├── config.py
│   │   └── security.py
│   ├── db/                 # Database setup
│   │   ├── session.py
│   │   └── base.py
│   ├── models/             # SQLAlchemy models
│   │   ├── user.py
│   │   ├── restaurant.py
│   │   ├── food.py
│   │   ├── order.py
│   │   └── post.py
│   ├── schemas/            # Pydantic schemas
│   │   ├── user.py
│   │   ├── restaurant.py
│   │   ├── food.py
│   │   ├── order.py
│   │   └── post.py
│   ├── services/           # Business logic
│   │   └── cloudinary_service.py
│   └── main.py             # FastAPI app
├── .env                    # Environment variables
├── .env.example            # Example env file
├── requirements.txt        # Python dependencies
├── alembic.ini             # Alembic config
└── README.md               # This file
```

---

## Database Schema

### Users
- id, email, full_name, hashed_password, role, is_active, google_id, created_at

### Restaurants
- id, owner_id, name, address, phone, email, latitude, longitude, status, created_at

### Foods
- id, restaurant_id, name, description, image, price, old_price, discount, quantity, expires_at

### Orders
- id, customer_id, restaurant_id, status, total_amount, pickup_time, created_at

### Posts
- id, author_id, text, image, location, restaurant_id, created_at

### PostLikes & PostComments
- Relationships for social features

---

## Common Issues & Solutions

### PostgreSQL not starting
```bash
brew services restart postgresql@14
```

### Port 8000 already in use
```bash
# Find process
lsof -i :8000

# Kill process
kill -9 <PID>
```

### Database connection error
- Check PostgreSQL is running
- Verify DATABASE_URL in .env
- Ensure database exists: `psql -l`

### Alembic migration errors
```bash
# Reset migrations
alembic downgrade base
alembic upgrade head
```

---

## Production Deployment

### Using Gunicorn (Recommended):

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### Environment Variables for Production:

```env
ENVIRONMENT=production
SECRET_KEY=<strong-random-secret>
DATABASE_URL=<production-postgres-url>
ALLOWED_ORIGINS=https://arzaqmeal.vercel.app
```

---

## Frontend Integration

Update frontend `.env`:

```env
VITE_API_URL=http://localhost:8000
```

Backend will be accessible from React frontend at the configured API URL.

---

## Support & Contact

For issues or questions:
- GitHub Issues
- Email: support@arzaq.kz

---

## License

MIT License - See LICENSE file

---

**Built with ❤️ for fighting food waste**
