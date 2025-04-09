#!/bin/bash
echo "Fixing phpMyAdmin configuration..."
PHPMYADMIN_PASSWORD=$(cat /dev/urandom | tr -dc "a-zA-Z0-9" | fold -w 16 | head -n 1)
echo "Generated password: $PHPMYADMIN_PASSWORD"
echo "Creating phpMyAdmin user and tables..."
sudo mysql -e "DROP USER IF EXISTS \"phpmyadmin\"@\"localhost\";"
sudo mysql -e "CREATE USER \"phpmyadmin\"@\"localhost\" IDENTIFIED BY \"$PHPMYADMIN_PASSWORD\";"
sudo mysql -e "GRANT ALL PRIVILEGES ON *.* TO \"phpmyadmin\"@\"localhost\" WITH GRANT OPTION;"
sudo mysql -e "FLUSH PRIVILEGES;"
sudo mysql < /usr/share/phpmyadmin/sql/create_tables.sql
echo "Creating new phpMyAdmin configuration file..."
sudo cp /etc/phpmyadmin/config.inc.php /etc/phpmyadmin/config.inc.php.bak
