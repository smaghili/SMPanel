# Project Structure

## System Architecture

```
+---------------------+       +---------------------+
|                     |       |                     |
|   Telegram Bot      |       |    Admin Panel      |
|                     |       |                     |
+----------+----------+       +---------+-----------+
           |                            |
           |                            |
+----------v----------------------------v-----------+
|                                                   |
|                  SMPanel Core                     |
|                                                   |
+---+-------------------+---------------+---+-------+
    |                   |                   |
    |                   |                   |
+---v---+         +-----v-----+       +----v----+
|       |         |           |       |         |
|  API  |         | Database  |       | Payment |
| Client|         | Service   |       | Gateway |
|       |         |           |       |         |
+---+---+         +-----------+       +---------+
    |
    |
+---v---+
|       |
| 3x-ui |
| Panel |
|       |
+-------+
```

## Directory Structure

```
SMPanel/
├── README.md
├── database_schema.md
├── api_endpoints.md
├── project_structure.md
├── src/
│   ├── bot/
│   │   ├── index.js           # Telegram bot initialization
│   │   ├── commands/          # Bot commands
│   │   ├── middlewares/       # Bot middlewares
│   │   └── scenes/            # Bot conversation scenes
│   ├── api/
│   │   ├── client.js          # 3x-ui API client
│   │   ├── routes/            # API routes
│   │   └── middlewares/       # API middlewares
│   ├── db/
│   │   ├── models/            # Database models
│   │   └── migrations/        # Database migrations
│   ├── services/
│   │   ├── panel.js           # Panel management service
│   │   ├── user.js            # User management service
│   │   ├── inbound.js         # Inbound management service
│   │   ├── client.js          # Client management service
│   │   ├── subscription.js    # Subscription management service
│   │   └── payment.js         # Payment processing service
│   ├── utils/
│   │   ├── logger.js          # Logging utility
│   │   └── helpers.js         # Helper functions
│   └── admin/
│       ├── index.js           # Admin panel initialization
│       └── routes/            # Admin panel routes
├── config/
│   ├── default.js             # Default configuration
│   ├── development.js         # Development configuration
│   └── production.js          # Production configuration
└── package.json
```

## Main Components

1. **Telegram Bot**: User interface for customers and resellers
2. **Admin Panel**: Web interface for administrators
3. **API Client**: Interface with 3x-ui panels
4. **Database Service**: Manage data persistence
5. **Payment Gateway**: Handle payment processing

## Data Flow

1. User interacts with the Telegram bot
2. Bot processes commands and triggers appropriate service methods
3. Services interact with the database and API client as needed
4. API client communicates with 3x-ui panels
5. Results are returned to the user through the bot 