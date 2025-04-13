-- SMPanel Database Initialization Script
-- This script creates the panels table if it doesn't exist
-- If the table already exists, its data will be preserved

-- Create panels table if not exists
CREATE TABLE IF NOT EXISTS panels (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    panel_type VARCHAR(50) DEFAULT '3x-ui' COMMENT 'Type of panel: 3x-ui or marzban',
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
); 

-- Shop Module Tables

-- Create categories table if not exists
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    image_url VARCHAR(255),
    inbound_ports TEXT COMMENT 'JSON array of inbound ports [port1, port2, ...]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Create category_panel table for many-to-many relationship between categories and panels
CREATE TABLE IF NOT EXISTS category_panel (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT NOT NULL,
    panel_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
    FOREIGN KEY (panel_id) REFERENCES panels(id) ON DELETE CASCADE,
    UNIQUE KEY (category_id, panel_id) COMMENT 'Prevent duplicate relationships'
);

-- Create products table if not exists
CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    data_limit INT NOT NULL COMMENT 'Data limit in GB',
    price DECIMAL(10, 2) NOT NULL,
    category_id INT,
    users_limit INT NOT NULL DEFAULT 1 COMMENT 'Number of users allowed',
    duration INT NOT NULL COMMENT 'Duration in days',
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
);

-- Create product_panel table for many-to-many relationship between products and panels
CREATE TABLE IF NOT EXISTS product_panel (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    panel_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (panel_id) REFERENCES panels(id) ON DELETE CASCADE,
    UNIQUE KEY (product_id, panel_id) COMMENT 'Prevent duplicate relationships'
);

-- Create orders table if not exists
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT,
    user_id INT NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' COMMENT 'pending, completed, cancelled',
    payment_status VARCHAR(50) DEFAULT 'unpaid' COMMENT 'paid, unpaid, refunded',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
);

-- Create discount_codes table if not exists
CREATE TABLE IF NOT EXISTS discount_codes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    percentage INT NOT NULL COMMENT 'Discount percentage',
    expiry_date DATETIME,
    min_purchase DECIMAL(10, 2) DEFAULT 0 COMMENT 'Minimum purchase amount',
    max_discount DECIMAL(10, 2) COMMENT 'Maximum discount amount',
    usage_limit INT COMMENT 'Maximum number of uses',
    times_used INT DEFAULT 0 COMMENT 'Number of times used',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Create gift_codes table if not exists
CREATE TABLE IF NOT EXISTS gift_codes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    amount DECIMAL(10, 2) NOT NULL COMMENT 'Gift amount',
    expiry_date DATETIME,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Create gift_code_usages table if not exists
CREATE TABLE IF NOT EXISTS gift_code_usages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    gift_code_id INT NOT NULL,
    user_id INT NOT NULL,
    order_id INT NOT NULL,
    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (gift_code_id) REFERENCES gift_codes(id) ON DELETE CASCADE,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    UNIQUE KEY (gift_code_id, user_id) COMMENT 'Ensures each user can use a gift code only once'
); 