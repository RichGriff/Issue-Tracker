# Issue Tracker
## Projedct around learning Python & FastAPI

A hands-on project where I explored FastAPI's core features and learned how to build modern Python web APIs.

## Overview

I built this project to learn FastAPI, a modern, fast web framework for building APIs with Python. Through practical implementation, I've gained experience with the fundamental concepts that make FastAPI powerful for API development.

## What I've Learned

Through this project, I've implemented and learned the following FastAPI features:

- **Route Definitions** - I can now create endpoints with path parameters, query parameters, and request bodies
- **Pydantic Models** - I've learned how to use runtime data validation and serialization (similar to Zod, but built for Python)
- **Dependency Injection** - I understand how to create reusable components and share logic across routes
- **OpenAPI Auto-Documentation** - I've seen how FastAPI automatically generates interactive API docs at `/docs` and `/redoc`
- **Database Integration with SQLAlchemy** - I've implemented database connections, models, and queries using SQLAlchemy ORM
- **Background Tasks** - I can now run operations after returning a response without blocking the main thread

**Note:** I focused on synchronous routes for this project. I haven't explored async routes yet.

## Prerequisites

Before starting this project, I made sure I had:

- Python 3.8 or higher
- Basic understanding of Python and REST APIs
- pip (Python package installer)

## Installation

Here's how I set up the project:

1. Create the project:
```bash
mkdir fastapi-issue-tracker
cd fastapi-learning-project
uv init .
```

2. Create a virtual environment:
```bash
uv venv
```

3. Install dependencies:
```bash
uv add fastapi[standard] sqlalchemy psycopg2
```

## Running the Application

I run the development server with:

```bash
uvicorn main:app --reload
```

The API is then available at `http://localhost:8000`

## Exploring What I Built

Once running, I can visit these URLs to interact with the API:

- **Swagger UI**: http://localhost:8000/docs - Interactive API documentation
- **ReDoc**: http://localhost:8000/redoc - Alternative documentation interface
- **OpenAPI Schema**: http://localhost:8000/openapi.json - Raw OpenAPI specification

## Project Structure

Here's how I organized my code:

```
.
├── main.py                 # Application entry point
├── pyproject.toml          # Lists projects dependencies
└── app                     # Folder to contain source code
  ├── models/               # Pydantic models for request/response validation
  ├── routes/               # API route definitions
  ├── database/             # SQLAlchemy models, database configuration, and session management
  ├── middleware/           # Creating custom middleware functions
  └── tasks/                # Background task definitions
```

## Key Concepts I Explored

### 1. Route Definitions
I learned how to create endpoints with different HTTP methods, handle path and query parameters, and structure my API logically.

### 2. Pydantic Models
I now understand how FastAPI uses Pydantic for automatic request validation, serialization, and generating API schemas. This provides runtime type checking similar to Zod in TypeScript, which I was already familiar with.

### 3. Dependency Injection
I discovered how to create reusable dependencies for database connections, authentication, shared logic, and more. I particularly enjoyed learning how dependencies can depend on other dependencies, creating a powerful composition pattern.

### 4. OpenAPI Auto-Documentation
One of my favorite features - I love how FastAPI automatically generates interactive documentation based on my code, making API exploration and testing seamless.

### 5. Database Integration with SQLAlchemy
I learned how to integrate SQLAlchemy with FastAPI to manage database operations. This included:

- Setting up database connections and session management
- Creating SQLAlchemy models to represent database tables
- Using dependency injection to provide database sessions to routes
- Performing CRUD operations (Create, Read, Update, Delete)
- Understanding the relationship between SQLAlchemy models (for the database) and Pydantic models (for API validation)

### 6. Background Tasks
I learned to execute operations after sending a response, which is perfect for sending emails, processing data, or logging without slowing down my API responses.

## Resources That Helped Me

- [FastAPI Official Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)

## What I Want to Learn Next

Now that I've completed this project, I'm planning to explore:

- Async routes with `async def` for improved performance
- Advanced SQLAlchemy features like relationships, migrations with Alembic, and query optimization
- Authentication and authorization
- Testing with pytest
- Deployment strategies

## Contributing

If you have suggestions or improvements, feel free to open issues or submit pull requests!

## License

MIT
