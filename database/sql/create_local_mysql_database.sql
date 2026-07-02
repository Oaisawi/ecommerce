CREATE DATABASE IF NOT EXISTS ecommerce_store
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'ecommerce_user'@'localhost' IDENTIFIED BY 'change_this_password';

GRANT ALL PRIVILEGES ON ecommerce_store.* TO 'ecommerce_user'@'localhost';

FLUSH PRIVILEGES;

-- After creating the database, set:
-- DATABASE_URL=mysql://ecommerce_user:change_this_password@127.0.0.1:3306/ecommerce_store
-- Then run:
-- python manage.py migrate
