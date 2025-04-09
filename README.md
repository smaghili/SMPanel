# SMPanel - VPN Panel Management Bot

A Telegram bot for selling and managing VPN panels.

## Features
- User management
- Panel configuration
- Inbound management
- Client account creation and management
- Subscription handling
- Payment processing
- Admin dashboard

## Installation

The project includes an installation script that will set up all required dependencies:

1. Make the installation script executable:
   ```bash
   chmod +x scripts/install.sh
   ```

2. Run the installation script:
   ```bash
   ./scripts/install.sh
   ```

The script will:
- Install and configure PostgreSQL database
- Install phpMyAdmin for database management
- Generate secure random passwords
- Set up the basic project structure

For more details, see [Installation Guide](scripts/README.md).

## Database Structure
The system uses the following database tables:

1. **users** - Store user information
2. **panels** - Store VPN panel information
3. **inbounds** - Manage inbound connections
4. **clients** - Store client accounts
5. **subscriptions** - Manage subscription information
6. **transactions** - Track financial transactions
7. **settings** - Store system configuration

## API Integration
This project integrates with the 3x-ui API for VPN panel management. 