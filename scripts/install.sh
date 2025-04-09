#!/bin/bash

# Colors for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color
CHECK_MARK='\xE2\x9C\x85'
CROSS_MARK='\xE2\x9D\x8C'

# Error handling
set -e  # Exit on error

# Function to handle errors
handle_error() {
    echo -e "\n${RED}${CROSS_MARK} Error occurred at line $1. Installation aborted.${NC}"
    exit 1
}

# Set up error trap
trap 'handle_error $LINENO' ERR

echo -e "${GREEN}===== SMPanel Installation Script =====${NC}"
echo -e "This script will check and install required dependencies for SMPanel"
echo -e "- MariaDB database server"
echo -e "- phpMyAdmin for database management"
echo -e "- Telegram Bot configuration"
echo

# Update package lists
echo -e "\n${YELLOW}Updating package lists...${NC}"
sudo apt-get update
echo -e "${GREEN}Package lists updated.${NC}"

# Function to check and install a package
check_and_install() {
    package_name=$1
    display_name=$2
    
    echo -e "\n${YELLOW}Checking $display_name...${NC}"
    
    if dpkg -s $package_name >/dev/null 2>&1; then
        echo -e "${GREEN}${CHECK_MARK} $display_name is already installed.${NC}"
        return 0
    else
        echo -e "${YELLOW}Installing $display_name...${NC}"
        sudo apt-get install -y $package_name
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}${CHECK_MARK} $display_name installed successfully.${NC}"
            return 0
        else
            echo -e "${RED}${CROSS_MARK} Failed to install $display_name.${NC}"
            return 1
        fi
    fi
}

# Function to generate secure random password (avoid special characters for SQL safety)
generate_password() {
    # Generate a random password with lowercase, uppercase, and numbers (16 characters)
    # Avoiding special characters that might need escaping in SQL
    password=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 16 | head -n 1)
    echo "$password"
}

# Function to generate secure random username
generate_username() {
    # Generate a random username with lowercase, uppercase, and numbers (8 characters)
    username=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 8 | head -n 1)
    echo "$username"
}

# Save passwords to a file
CREDENTIALS_FILE="$(pwd)/smpanel_credentials.txt"
echo "# SMPanel Installation Credentials" > $CREDENTIALS_FILE
echo "# Generated on $(date)" >> $CREDENTIALS_FILE
echo "# IMPORTANT: Store this information securely and delete this file after setup" >> $CREDENTIALS_FILE
echo "" >> $CREDENTIALS_FILE

# Check and install MariaDB
check_and_install mariadb-server "MariaDB"

# Make sure MariaDB is running
echo -e "\n${YELLOW}Making sure MariaDB service is running...${NC}"
sudo systemctl start mariadb
sudo systemctl enable mariadb
echo -e "${GREEN}${CHECK_MARK} MariaDB service is running.${NC}"

# Check if our database exists
echo -e "\n${YELLOW}Checking for existing SMPanel database...${NC}"
if echo "SHOW DATABASES LIKE 'smpanel';" | sudo mysql -s | grep -q smpanel; then
    echo -e "${GREEN}${CHECK_MARK} SMPanel database already exists.${NC}"
    
    # We still need these variables for later use
    DB_NAME="smpanel"
    
    # Try to get the existing user or create a new one
    echo -e "\n${YELLOW}Checking for existing SMPanel database user...${NC}"
    EXISTING_USER=$(echo "SELECT user FROM mysql.user WHERE user LIKE 'smpanel_%' LIMIT 1;" | sudo mysql -s)
    
    if [ -n "$EXISTING_USER" ]; then
        DB_USER=$EXISTING_USER
        echo -e "${GREEN}${CHECK_MARK} Using existing database user: $DB_USER${NC}"
        # Generate a new password for the existing user
        MYSQL_PASSWORD=$(generate_password)
        echo -e "\n${YELLOW}Setting new password for $DB_USER...${NC}"
        echo "ALTER USER '$DB_USER'@'localhost' IDENTIFIED BY '$MYSQL_PASSWORD';" | sudo mysql
        echo "FLUSH PRIVILEGES;" | sudo mysql
        
        echo -e "${GREEN}${CHECK_MARK} Password updated successfully.${NC}"
    else
        # Create new user
        echo -e "\n${YELLOW}Creating new MariaDB user for SMPanel...${NC}"
        DB_USER="smpanel_$(generate_username)"
        MYSQL_PASSWORD=$(generate_password)
        
        # Create user with secure password
        echo "CREATE USER '$DB_USER'@'localhost' IDENTIFIED BY '$MYSQL_PASSWORD';" | sudo mysql
        echo "GRANT ALL PRIVILEGES ON smpanel.* TO '$DB_USER'@'localhost';" | sudo mysql
        echo "FLUSH PRIVILEGES;" | sudo mysql
        echo -e "${GREEN}${CHECK_MARK} Created new database user: $DB_USER${NC}"
    fi
    
    # Verify connection works with the new credentials
    echo -e "\n${YELLOW}Verifying database connection...${NC}"
    mysql -h localhost -u "$DB_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1;" smpanel > /dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}${CHECK_MARK} Database connection verified.${NC}"
    else
        echo -e "${RED}${CROSS_MARK} Could not connect to database with the new credentials.${NC}"
        exit 1
    fi
    
    # Save credentials even for existing database
    echo "## MariaDB" >> $CREDENTIALS_FILE
    echo "DATABASE_NAME: $DB_NAME" >> $CREDENTIALS_FILE
    echo "DATABASE_USER: $DB_USER" >> $CREDENTIALS_FILE
    echo "DATABASE_PASSWORD: $MYSQL_PASSWORD" >> $CREDENTIALS_FILE
    echo "" >> $CREDENTIALS_FILE
else
    echo -e "${YELLOW}Creating SMPanel database and user...${NC}"
    # Generate MariaDB password and username
    MYSQL_PASSWORD=$(generate_password)
    DB_NAME="smpanel"
    DB_USER="smpanel_$(generate_username)"
    
    # Create SMPanel database and user
    echo "CREATE DATABASE $DB_NAME;" | sudo mysql
    echo "CREATE USER '$DB_USER'@'localhost' IDENTIFIED BY '$MYSQL_PASSWORD';" | sudo mysql
    echo "GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';" | sudo mysql
    echo "FLUSH PRIVILEGES;" | sudo mysql
    
    # Verify connection works with the new credentials
    echo -e "\n${YELLOW}Verifying database connection...${NC}"
    mysql -h localhost -u "$DB_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1;" $DB_NAME > /dev/null
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}${CHECK_MARK} Database connection verified.${NC}"
    else
        echo -e "${RED}${CROSS_MARK} Could not connect to database with the new credentials.${NC}"
        exit 1
    fi
    
    # Save MariaDB credentials
    echo "## MariaDB" >> $CREDENTIALS_FILE
    echo "DATABASE_NAME: $DB_NAME" >> $CREDENTIALS_FILE
    echo "DATABASE_USER: $DB_USER" >> $CREDENTIALS_FILE
    echo "DATABASE_PASSWORD: $MYSQL_PASSWORD" >> $CREDENTIALS_FILE
    echo "" >> $CREDENTIALS_FILE
    
    echo -e "${GREEN}${CHECK_MARK} Database setup complete!${NC}"
fi

# Check and install Apache (needed for phpMyAdmin)
check_and_install apache2 "Apache Web Server"

# Check and install PHP and all required extensions at once
echo -e "\n${YELLOW}Checking PHP and required extensions...${NC}"
if dpkg -s php php-mbstring php-zip php-gd php-json php-curl php-mysql >/dev/null 2>&1; then
    echo -e "${GREEN}${CHECK_MARK} PHP and all required extensions are already installed.${NC}"
else
    echo -e "${YELLOW}Installing PHP and all required extensions...${NC}"
    sudo apt-get install -y php php-mbstring php-zip php-gd php-json php-curl php-mysql
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}${CHECK_MARK} PHP and all required extensions installed successfully.${NC}"
    else
        echo -e "${RED}${CROSS_MARK} Failed to install PHP and its extensions.${NC}"
        exit 1
    fi
fi

# Check and install phpMyAdmin
echo -e "\n${YELLOW}Checking phpMyAdmin...${NC}"
if ! dpkg -l | grep -q phpmyadmin; then
    echo -e "${YELLOW}phpMyAdmin is not installed. Installing...${NC}"
    
    # Set non-interactive installation for phpMyAdmin
    # Pre-configure the phpMyAdmin installation to skip interactive prompts
    export DEBIAN_FRONTEND=noninteractive
    
    # Install phpMyAdmin with pre-defined answers
    sudo debconf-set-selections <<< "phpmyadmin phpmyadmin/dbconfig-install boolean true"
    sudo debconf-set-selections <<< "phpmyadmin phpmyadmin/app-password-confirm password $MYSQL_PASSWORD"
    sudo debconf-set-selections <<< "phpmyadmin phpmyadmin/mysql/admin-pass password $MYSQL_PASSWORD"
    sudo debconf-set-selections <<< "phpmyadmin phpmyadmin/mysql/app-pass password $MYSQL_PASSWORD"
    sudo debconf-set-selections <<< "phpmyadmin phpmyadmin/reconfigure-webserver multiselect apache2"
    
    # Install phpMyAdmin
    sudo apt-get install -y phpmyadmin
    
    # Check if installation was successful
    if dpkg -l | grep -q phpmyadmin; then
        echo -e "${GREEN}${CHECK_MARK} phpMyAdmin installed successfully.${NC}"
        
        # Create a symbolic link to ensure phpMyAdmin is accessible
        sudo ln -sf /usr/share/phpmyadmin /var/www/html/phpmyadmin
        
        # Create phpMyAdmin apache configuration in case it's missing
        echo -e "${YELLOW}Setting up phpMyAdmin Apache configuration...${NC}"
        sudo bash -c 'cat > /etc/apache2/conf-available/phpmyadmin.conf << EOL
# phpMyAdmin Apache configuration
Alias /phpmyadmin /usr/share/phpmyadmin

<Directory /usr/share/phpmyadmin>
    Options FollowSymLinks
    DirectoryIndex index.php
    AllowOverride None
    Require all granted
</Directory>
EOL'
        
        # Enable the phpMyAdmin configuration
        sudo a2enconf phpmyadmin
        
        # Restart Apache
        sudo systemctl restart apache2
        
        # Run the phpMyAdmin setup script
        echo -e "\n${YELLOW}Running phpMyAdmin advanced setup...${NC}"
        # Make the script executable first
        chmod +x scripts/phpmyadmin_setup.sh
        # Run the script with database credentials and capture the output
        PMA_CREDENTIALS=$(./scripts/phpmyadmin_setup.sh "$DB_USER" "$MYSQL_PASSWORD")
        # Extract username and password from returned string
        PMA_USER=$(echo $PMA_CREDENTIALS | cut -d',' -f1)
        PMA_PASS=$(echo $PMA_CREDENTIALS | cut -d',' -f2)
        echo -e "${GREEN}${CHECK_MARK} phpMyAdmin advanced setup completed.${NC}"
        
        # Save phpMyAdmin credentials
        echo "## phpMyAdmin" >> $CREDENTIALS_FILE
        echo "PHPMYADMIN_URL: http://$(hostname -I | awk '{print $1}')/phpmyadmin" >> $CREDENTIALS_FILE
        echo "DATABASE_USER (For database access): $DB_USER" >> $CREDENTIALS_FILE
        echo "DATABASE_PASSWORD (For database access): $MYSQL_PASSWORD" >> $CREDENTIALS_FILE
        echo "PHPMYADMIN_CONTROL_USER: $PMA_USER" >> $CREDENTIALS_FILE
        echo "PHPMYADMIN_CONTROL_PASSWORD: $PMA_PASS" >> $CREDENTIALS_FILE
        echo "" >> $CREDENTIALS_FILE
        
        echo -e "${GREEN}${CHECK_MARK} phpMyAdmin configured successfully.${NC}"
    else
        echo -e "${RED}${CROSS_MARK} Failed to install phpMyAdmin.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}${CHECK_MARK} phpMyAdmin is already installed.${NC}"
    
    # Create a symbolic link to ensure phpMyAdmin is accessible (even if it already exists)
    sudo ln -sf /usr/share/phpmyadmin /var/www/html/phpmyadmin
    
    # Check if the Apache configuration exists, create if missing
    if [ ! -f /etc/apache2/conf-available/phpmyadmin.conf ]; then
        echo -e "${YELLOW}Setting up phpMyAdmin Apache configuration...${NC}"
        sudo bash -c 'cat > /etc/apache2/conf-available/phpmyadmin.conf << EOL
# phpMyAdmin Apache configuration
Alias /phpmyadmin /usr/share/phpmyadmin

<Directory /usr/share/phpmyadmin>
    Options FollowSymLinks
    DirectoryIndex index.php
    AllowOverride None
    Require all granted
</Directory>
EOL'
        
        # Enable the phpMyAdmin configuration
        sudo a2enconf phpmyadmin
        
        # Restart Apache
        sudo systemctl restart apache2
    fi
    
    # Run the phpMyAdmin setup script
    echo -e "\n${YELLOW}Running phpMyAdmin advanced setup...${NC}"
    # Make the script executable first
    chmod +x scripts/phpmyadmin_setup.sh
    # Run the script with database credentials and capture the output
    PMA_CREDENTIALS=$(./scripts/phpmyadmin_setup.sh "$DB_USER" "$MYSQL_PASSWORD")
    # Extract username and password from returned string
    PMA_USER=$(echo $PMA_CREDENTIALS | cut -d',' -f1)
    PMA_PASS=$(echo $PMA_CREDENTIALS | cut -d',' -f2)
    echo -e "${GREEN}${CHECK_MARK} phpMyAdmin advanced setup completed.${NC}"
    
    # Save phpMyAdmin credentials
    echo "## phpMyAdmin" >> $CREDENTIALS_FILE
    echo "PHPMYADMIN_URL: http://$(hostname -I | awk '{print $1}')/phpmyadmin" >> $CREDENTIALS_FILE
    echo "DATABASE_USER (For database access): $DB_USER" >> $CREDENTIALS_FILE
    echo "DATABASE_PASSWORD (For database access): $MYSQL_PASSWORD" >> $CREDENTIALS_FILE
    echo "PHPMYADMIN_CONTROL_USER: $PMA_USER" >> $CREDENTIALS_FILE
    echo "PHPMYADMIN_CONTROL_PASSWORD: $PMA_PASS" >> $CREDENTIALS_FILE
    echo "" >> $CREDENTIALS_FILE
    
    echo -e "${GREEN}${CHECK_MARK} phpMyAdmin configuration verified.${NC}"
fi

# Check and install Python and required packages
check_and_install python3 "Python 3"
check_and_install python3-pip "Python pip"
check_and_install python3-venv "Python virtual environment"

# Create necessary directories for SMPanel project
echo -e "\n${YELLOW}Setting up project directory structure...${NC}"
mkdir -p src/{bot/{commands,middlewares,scenes},api/{routes,middlewares},db/{models,migrations},services,utils,admin/routes} config
echo -e "${GREEN}${CHECK_MARK} Project directory structure created.${NC}"

# Create virtual environment
echo -e "\n${YELLOW}Creating Python virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate
echo -e "${GREEN}${CHECK_MARK} Virtual environment created and activated.${NC}"

# Install required Python packages
echo -e "\n${YELLOW}Installing required Python packages...${NC}"
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}${CHECK_MARK} Python packages installed from requirements.txt.${NC}"
    else
        echo -e "${RED}${CROSS_MARK} Failed to install some Python packages.${NC}"
        exit 1
    fi
else
    pip install python-telegram-bot mysql-connector-python python-dotenv
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}${CHECK_MARK} Python packages installed.${NC}"
    else
        echo -e "${RED}${CROSS_MARK} Failed to install Python packages.${NC}"
        exit 1
    fi
fi

# Initialize database with schema
echo -e "\n${YELLOW}Initializing database schema...${NC}"
if [ -f "src/db/panels.sql" ]; then
    # Execute SQL script to create tables (only if they don't exist)
    # This will preserve existing data
    mysql -h localhost -u "$DB_USER" -p"$MYSQL_PASSWORD" $DB_NAME < src/db/panels.sql
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}${CHECK_MARK} Database schema initialized successfully!${NC}"
    else
        echo -e "${RED}${CROSS_MARK} Error initializing database schema. Check error messages above.${NC}"
        exit 1
    fi
else
    echo -e "${RED}${CROSS_MARK} Database initialization script not found. Skipping schema creation.${NC}"
    echo -e "${YELLOW}You will need to manually create the database schema.${NC}"
fi

# Display credentials to the user (complete details)
echo -e "\n${GREEN}===== Your Access Credentials =====${NC}"

echo -e "\n${GREEN}MariaDB Database Information${NC}"
echo -e "Database Name: $DB_NAME"
echo -e "Database Host: localhost"
echo -e "Database Port: 3306"
echo -e "Database Username: $DB_USER"
echo -e "Database Password: $MYSQL_PASSWORD"

echo -e "\n${GREEN}phpMyAdmin Information${NC}"
echo -e "phpMyAdmin URL: http://$(hostname -I | awk '{print $1}')/phpmyadmin"
echo -e "phpMyAdmin Port: 80"
echo -e "Access via browser: http://$(hostname -I | awk '{print $1}'):80/phpmyadmin"
echo -e "Login with MariaDB credentials (For database access):"
echo -e "  Username: $DB_USER"
echo -e "  Password: $MYSQL_PASSWORD"
echo -e "\nphpMyAdmin Control User (For internal phpMyAdmin functions):"
echo -e "  Username: $PMA_USER"
echo -e "  Password: $PMA_PASS"

echo -e "\n${RED}PLEASE SAVE THESE CREDENTIALS SECURELY BEFORE CONTINUING${NC}"
echo -e "Press Enter to continue with Telegram Bot setup..."
read

# Get Telegram Bot Token and Admin ID
echo -e "\n${YELLOW}Configuring Telegram Bot...${NC}"
echo -e "Please enter your Telegram Bot Token (get it from @BotFather):"
read -p "> " TELEGRAM_BOT_TOKEN

# Validate token format
while [[ ! $TELEGRAM_BOT_TOKEN =~ ^[0-9]+:[a-zA-Z0-9_-]+$ ]]; do
    echo -e "${RED}Invalid token format. Please enter a valid Telegram Bot Token:${NC}"
    read -p "> " TELEGRAM_BOT_TOKEN
done

echo -e "Please enter the Admin's Telegram User ID (numeric ID, get it from @userinfobot):"
read -p "> " ADMIN_TELEGRAM_ID

# Validate Admin ID format
while [[ ! $ADMIN_TELEGRAM_ID =~ ^[0-9]+$ ]]; do
    echo -e "${RED}Invalid ID format. Please enter a valid numeric Telegram User ID:${NC}"
    read -p "> " ADMIN_TELEGRAM_ID
done

# Save Telegram credentials
echo "## Telegram Bot" >> $CREDENTIALS_FILE
echo "TELEGRAM_BOT_TOKEN: $TELEGRAM_BOT_TOKEN" >> $CREDENTIALS_FILE
echo "ADMIN_TELEGRAM_ID: $ADMIN_TELEGRAM_ID" >> $CREDENTIALS_FILE
echo "" >> $CREDENTIALS_FILE

# Create config file
echo -e "\n${YELLOW}Creating configuration file...${NC}"
mkdir -p config
cat > config/config.py << EOL
# SMPanel Configuration

# Database settings
DATABASE = {
    'host': 'localhost',
    'database': '$DB_NAME',
    'user': '$DB_USER',
    'password': '$MYSQL_PASSWORD'
}

# Telegram Bot settings
TELEGRAM = {
    'token': '$TELEGRAM_BOT_TOKEN',
    'admin_id': $ADMIN_TELEGRAM_ID
}
EOL
echo -e "${GREEN}${CHECK_MARK} Configuration file created.${NC}"

# Create .env file
echo -e "\n${YELLOW}Creating .env file...${NC}"
cat > .env << EOL
# SMPanel Environment Variables

# Database
DB_HOST=localhost
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$MYSQL_PASSWORD

# Telegram
TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN
ADMIN_TELEGRAM_ID=$ADMIN_TELEGRAM_ID
EOL
echo -e "${GREEN}${CHECK_MARK} Environment file created.${NC}"

# Create a startup script for the bot
echo -e "\n${YELLOW}Creating bot startup script...${NC}"
cat > start_bot.sh << EOL
#!/bin/bash
source venv/bin/activate
python src/bot/index.py
EOL
chmod +x start_bot.sh
echo -e "${GREEN}${CHECK_MARK} Bot startup script created.${NC}"

# Create a first-run script to send welcome message to admin
echo -e "\n${YELLOW}Creating first-run script to send welcome message...${NC}"
cat > src/bot/first_run.py << EOL
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from telegram import Bot
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get bot token and admin ID from environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_TELEGRAM_ID = int(os.getenv('ADMIN_TELEGRAM_ID'))

async def send_welcome_message():
    """Send welcome message to admin."""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    # Welcome message in Persian
    welcome_message = """
🎉 *نصب SMPanel با موفقیت انجام شد!*

سلام ادمین عزیز،
ربات SMPanel با موفقیت نصب و راه‌اندازی شد. اکنون می‌توانید از ربات برای مدیریت پنل‌های خود استفاده کنید.

برای شروع، دستور /start را ارسال کنید.

با تشکر،
تیم SMPanel
"""
    
    try:
        # Send welcome message to admin
        print("Sending welcome message to admin...")
        await bot.send_message(
            chat_id=ADMIN_TELEGRAM_ID,
            text=welcome_message,
            parse_mode='Markdown'
        )
        print("Welcome message sent successfully to admin.")
    except Exception as e:
        print(f"Error sending welcome message: {e}")

if __name__ == "__main__":
    # Run the async function
    asyncio.run(send_welcome_message())
EOL
chmod +x src/bot/first_run.py
echo -e "${GREEN}${CHECK_MARK} First-run script created.${NC}"

# Output success message
echo -e "\n${GREEN}===== Installation Complete! =====${NC}"
echo -e "${YELLOW}Your credentials have been saved to:${NC} $CREDENTIALS_FILE"
echo -e "${RED}IMPORTANT: Make sure to secure this file and delete it after setup${NC}"

# Display final credentials to the user (complete details)
echo -e "\n${GREEN}===== Your Final Access Credentials =====${NC}"

echo -e "\n${GREEN}MariaDB Database Information${NC}"
echo -e "Database Name: $DB_NAME"
echo -e "Database Host: localhost"
echo -e "Database Port: 3306"
echo -e "Database Username: $DB_USER"
echo -e "Database Password: $MYSQL_PASSWORD"

echo -e "\n${GREEN}phpMyAdmin Information${NC}"
echo -e "phpMyAdmin URL: http://$(hostname -I | awk '{print $1}')/phpmyadmin"
echo -e "phpMyAdmin Port: 80"
echo -e "Access via browser: http://$(hostname -I | awk '{print $1}'):80/phpmyadmin"
echo -e "Login with MariaDB credentials (For database access):"
echo -e "  Username: $DB_USER"
echo -e "  Password: $MYSQL_PASSWORD"
echo -e "\nphpMyAdmin Control User (For internal phpMyAdmin functions):"
echo -e "  Username: $PMA_USER"
echo -e "  Password: $PMA_PASS"

echo -e "\n${GREEN}Telegram Bot Information${NC}"
echo -e "Bot Token: $TELEGRAM_BOT_TOKEN"
echo -e "Admin ID: $ADMIN_TELEGRAM_ID"

echo -e "\n${RED}PLEASE SAVE THESE CREDENTIALS SECURELY${NC}"

# Send welcome message to admin
echo -e "\n${YELLOW}Sending welcome message to admin...${NC}"
python src/bot/first_run.py
echo -e "${GREEN}${CHECK_MARK} Welcome message sent to admin.${NC}"

# Start the bot in the background
echo -e "\n${YELLOW}Starting the bot in the background...${NC}"
echo -e "${GREEN}The bot is now running!${NC}"
echo -e "${YELLOW}You can stop the bot by pressing Ctrl+C${NC}"
echo
echo -e "${GREEN}Thank you for installing SMPanel!${NC}"

# Start the bot
./start_bot.sh 