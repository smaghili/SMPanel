# Database Schema for SMPanel

## 1. users
- **id**: INTEGER (Primary Key, Auto Increment)
- **username**: VARCHAR(255)
- **telegram_id**: VARCHAR(255) (Unique)
- **role**: ENUM('admin', 'reseller', 'customer')
- **balance**: DECIMAL(10,2) DEFAULT 0.00
- **created_at**: TIMESTAMP
- **updated_at**: TIMESTAMP

## 2. panels
- **id**: INTEGER (Primary Key, Auto Increment)
- **name**: VARCHAR(255)
- **url**: VARCHAR(255)
- **username**: VARCHAR(255)
- **password**: VARCHAR(255) (Encrypted)
- **status**: ENUM('active', 'inactive')
- **created_at**: TIMESTAMP
- **updated_at**: TIMESTAMP

## 3. inbounds
- **id**: INTEGER (Primary Key, Auto Increment)
- **panel_id**: INTEGER (Foreign Key to panels.id)
- **inbound_id**: INTEGER (ID from the 3x-ui API)
- **protocol**: VARCHAR(50)
- **port**: INTEGER
- **tag**: VARCHAR(255)
- **settings**: TEXT (JSON)
- **stream_settings**: TEXT (JSON)
- **sniffing**: TEXT (JSON)
- **remark**: VARCHAR(255)
- **listen**: VARCHAR(255)
- **total_bandwidth**: BIGINT
- **enable**: BOOLEAN
- **created_at**: TIMESTAMP
- **updated_at**: TIMESTAMP

## 4. clients
- **id**: INTEGER (Primary Key, Auto Increment)
- **user_id**: INTEGER (Foreign Key to users.id)
- **inbound_id**: INTEGER (Foreign Key to inbounds.id)
- **client_id**: VARCHAR(255) (ID from the 3x-ui API)
- **email**: VARCHAR(255)
- **uuid**: VARCHAR(255)
- **flow**: VARCHAR(50)
- **alter_id**: INTEGER
- **limit_ip**: INTEGER
- **total_bandwidth**: BIGINT
- **expire_time**: BIGINT
- **enable**: BOOLEAN
- **subscription_id**: INTEGER (Foreign Key to subscriptions.id)
- **created_at**: TIMESTAMP
- **updated_at**: TIMESTAMP

## 5. subscriptions
- **id**: INTEGER (Primary Key, Auto Increment)
- **name**: VARCHAR(255)
- **duration_days**: INTEGER
- **bandwidth_gb**: INTEGER
- **price**: DECIMAL(10,2)
- **concurrent_connections**: INTEGER
- **status**: ENUM('active', 'inactive')
- **created_at**: TIMESTAMP
- **updated_at**: TIMESTAMP

## 6. transactions
- **id**: INTEGER (Primary Key, Auto Increment)
- **user_id**: INTEGER (Foreign Key to users.id)
- **amount**: DECIMAL(10,2)
- **type**: ENUM('deposit', 'purchase', 'refund')
- **description**: TEXT
- **status**: ENUM('pending', 'completed', 'failed')
- **reference_id**: VARCHAR(255)
- **created_at**: TIMESTAMP
- **updated_at**: TIMESTAMP

## 7. client_subscriptions
- **id**: INTEGER (Primary Key, Auto Increment)
- **client_id**: INTEGER (Foreign Key to clients.id)
- **subscription_id**: INTEGER (Foreign Key to subscriptions.id)
- **start_date**: TIMESTAMP
- **end_date**: TIMESTAMP
- **status**: ENUM('active', 'expired', 'cancelled')
- **created_at**: TIMESTAMP
- **updated_at**: TIMESTAMP

## 8. settings
- **id**: INTEGER (Primary Key, Auto Increment)
- **key**: VARCHAR(255) (Unique)
- **value**: TEXT
- **created_at**: TIMESTAMP
- **updated_at**: TIMESTAMP 