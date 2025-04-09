# SMPanel Installation Script

This directory contains installation and setup scripts for the SMPanel project.

## Installation Script

The `install.sh` script helps you set up the required dependencies for SMPanel:

- PostgreSQL database server
- phpMyAdmin for database management
- Database schema initialization

### Usage

To run the installation script:

1. Make the script executable:
   ```bash
   chmod +x scripts/install.sh
   ```

2. Run the script:
   ```bash
   ./scripts/install.sh
   ```

### What the Script Does

- Checks if PostgreSQL is installed and installs it if needed
- Creates a dedicated database and user for the SMPanel application with a secure random password
- Checks if Apache and PHP are installed and installs them if needed (required for phpMyAdmin)
- Installs and configures phpMyAdmin with a secure random username and password
- Sets up the basic project directory structure
- Initializes the database with required tables using `database_init.sql`
- Saves all credentials to `smpanel_credentials.txt` in the project root

### Security Notes

- The script generates random secure usernames and passwords for PostgreSQL and phpMyAdmin
- All credentials are saved to a text file in the project directory
- After setup, you should securely store these credentials and **delete the credentials file**

## Database Initialization Script

The `database_init.sql` file contains SQL commands to create the database schema for SMPanel:

- Uses `CREATE TABLE IF NOT EXISTS` to preserve existing data if tables already exist
- Creates all necessary tables according to the project schema
- Sets up appropriate indexes for better performance
- Inserts default settings

Tables created:
- users
- panels
- inbounds
- clients
- subscriptions
- transactions
- settings

## After Installation

After running the installation script:

1. Review the generated credentials file
2. Update your database connection settings in `config/` files
3. Verify the database schema was created correctly
4. Secure or delete the credentials file

## Troubleshooting

If you encounter any issues during installation:

- Ensure you're running the script with sufficient permissions (sudo may be required)
- Check system logs for more detailed error information
- Make sure your system is up-to-date with `sudo apt-get update && sudo apt-get upgrade`
- If the database schema fails to initialize, you can manually run the SQL script:
  ```bash
  psql -h localhost -U [your_db_user] -d smpanel -f scripts/database_init.sql
  ``` 