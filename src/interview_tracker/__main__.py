"""Entry point for Interview Tracker application."""

import sys


def main():
    """Main entry point for the application."""
    # Initialize database
    from .data.database import get_db
    db = get_db()

    # Run the GUI application
    from .gui.app import run_app
    run_app()


if __name__ == "__main__":
    main()
