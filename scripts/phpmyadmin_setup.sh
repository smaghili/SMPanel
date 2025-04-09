#!/bin/bash

# Colors for better output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color
CHECK_MARK='\xE2\x9C\x85'
CROSS_MARK='\xE2\x9D\x8C'

# Get database credentials from environment
SMPanel_DB_USER="$1"
SMPanel_DB_PASS="$2"

# Generate random username and password for phpMyAdmin
generate_random() {
    cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w $1 | head -n 1
}

PMA_USER="pma_$(generate_random 8)"
PMA_PASS=$(generate_random 16)

# All echo output goes to stderr, not stdout
echo -e "${GREEN}===== Setting up phpMyAdmin =====${NC}" >&2

# Create dedicated phpMyAdmin user
echo -e "${YELLOW}Creating dedicated phpMyAdmin user...${NC}" >&2
sudo mysql -e "DROP USER IF EXISTS '$PMA_USER'@'localhost';"
sudo mysql -e "CREATE USER '$PMA_USER'@'localhost' IDENTIFIED BY '$PMA_PASS';"
sudo mysql -e "GRANT SELECT, INSERT, UPDATE, DELETE ON phpmyadmin.* TO '$PMA_USER'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"
echo -e "${GREEN}${CHECK_MARK} phpMyAdmin user created.${NC}" >&2

# Create phpMyAdmin tables
echo -e "${YELLOW}Creating phpMyAdmin tables...${NC}" >&2
sudo mysql < /usr/share/phpmyadmin/sql/create_tables.sql
echo -e "${GREEN}${CHECK_MARK} phpMyAdmin tables created.${NC}" >&2

# Create new configuration file
echo -e "${YELLOW}Creating new configuration file...${NC}" >&2
sudo cp /etc/phpmyadmin/config.inc.php /etc/phpmyadmin/config.inc.php.bak
# Generate random blowfish secret
BLOWFISH_SECRET=$(generate_random 32)
sudo tee /etc/phpmyadmin/config.inc.php > /dev/null << EOF
<?php
\$cfg['blowfish_secret'] = '$BLOWFISH_SECRET';
\$i = 0;
\$i++;
\$cfg['Servers'][\$i]['auth_type'] = 'cookie';
\$cfg['Servers'][\$i]['host'] = 'localhost';
\$cfg['Servers'][\$i]['compress'] = false;
\$cfg['Servers'][\$i]['AllowNoPassword'] = false;
\$cfg['Servers'][\$i]['controluser'] = '$PMA_USER';
\$cfg['Servers'][\$i]['controlpass'] = '$PMA_PASS';
\$cfg['Servers'][\$i]['pmadb'] = 'phpmyadmin';
\$cfg['Servers'][\$i]['bookmarktable'] = 'pma__bookmark';
\$cfg['Servers'][\$i]['relation'] = 'pma__relation';
\$cfg['Servers'][\$i]['table_info'] = 'pma__table_info';
\$cfg['Servers'][\$i]['table_coords'] = 'pma__table_coords';
\$cfg['Servers'][\$i]['pdf_pages'] = 'pma__pdf_pages';
\$cfg['Servers'][\$i]['column_info'] = 'pma__column_info';
\$cfg['Servers'][\$i]['history'] = 'pma__history';
\$cfg['Servers'][\$i]['table_uiprefs'] = 'pma__table_uiprefs';
\$cfg['Servers'][\$i]['tracking'] = 'pma__tracking';
\$cfg['Servers'][\$i]['userconfig'] = 'pma__userconfig';
\$cfg['Servers'][\$i]['recent'] = 'pma__recent';
\$cfg['Servers'][\$i]['favorite'] = 'pma__favorite';
\$cfg['Servers'][\$i]['users'] = 'pma__users';
\$cfg['Servers'][\$i]['usergroups'] = 'pma__usergroups';
\$cfg['Servers'][\$i]['navigationhiding'] = 'pma__navigationhiding';
\$cfg['Servers'][\$i]['savedsearches'] = 'pma__savedsearches';
\$cfg['Servers'][\$i]['central_columns'] = 'pma__central_columns';
\$cfg['Servers'][\$i]['designer_settings'] = 'pma__designer_settings';
\$cfg['Servers'][\$i]['export_templates'] = 'pma__export_templates';
\$cfg['UploadDir'] = '';
\$cfg['SaveDir'] = '';
EOF
echo -e "${GREEN}${CHECK_MARK} Configuration file updated.${NC}" >&2

# Ensure phpMyAdmin symlink exists
echo -e "${YELLOW}Ensuring phpMyAdmin symlink exists...${NC}" >&2
sudo ln -sf /usr/share/phpmyadmin /var/www/html/
echo -e "${GREEN}${CHECK_MARK} phpMyAdmin symlink created.${NC}" >&2

# Restart Apache
echo -e "${YELLOW}Restarting Apache...${NC}" >&2
sudo systemctl restart apache2
echo -e "${GREEN}${CHECK_MARK} Apache restarted.${NC}" >&2

# Return phpMyAdmin credentials to parent script (to stdout)
echo "$PMA_USER,$PMA_PASS"

echo -e "${GREEN}===== phpMyAdmin setup completed successfully! =====${NC}" >&2 