# Simple Pokemon Trainer Website

This project is a simple web application for Pokemon trainers. It's built with Python and uses the FastAPI framework for the backend. The frontend is built with HTML, CSS, and JavaScript.

## Features

- User registration and login
- Profile viewing with authorization
- Pokemon addition to a trainer's collection
- Pokemon creation (admin only)

## User Accounts

There are several pre-existing user accounts with hashed passwords in the trainers database:

- Username: sigma, Password: 1234
- Username: ligma, Password: 4321
- Username: prostochmonya, Password: qwerty
- Username: admin, Password: superheslo (Admin account)

## Authorization

Access to certain endpoints (`/api/pokemons`, `/api/pokemons/{pokedex_number}`, `/api/create`) is restricted to the admin user only. To view a profile, user authorization is required. The "add pokemon" and "create" buttons are available in the profile view. The "create" button is only visible and accessible to the admin user.

Authorization tokens expire after 15 minutes.

## Running the Application

The application is set to run on port 80 and will accept communication from any IP address. Any changes to the source files will automatically restart the application.
