# Telegram Marketplace Bot Project

## Project Structure

- `bot/`  
  Contains the Telegram bot logic and handlers.  
  Main bot file: `bot.py`

- `database/`  
  Contains database setup and access code.  
  Main setup file: `database_setup.py`

- `templates/`  
  HTML templates for web views and Telegram web app pages.

- `static/`  
  Static assets such as CSS, JavaScript, and images.

- `webapp/`  
  Web app related code (renamed from `web app/` for consistency).

## Description

This project implements a Telegram marketplace bot with features for browsing items, adding items, viewing stats, and admin management. It uses SQLite for data storage and includes a web app interface for enhanced user experience.

## How to Run

1. Install dependencies: `pip install -r requirements.txt`
2. Set up the database: `python database/database_setup.py`
3. Set environment variables: `TELEGRAM_BOT_TOKEN`, `WEB_APP_URL`, `ADMIN_USER_ID`
4. Run the bot: `python bot/bot.py`

## Features

- Browse marketplace items
- Add items for sale
- View seller statistics
- Admin panel for management
- Web app interface for enhanced UX
- Analytics and logging

## Technologies Used

- Python
- Telegram Bot API
- SQLite
- Flask (for web app)
- Bootstrap (for UI)
