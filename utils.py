import logging

def setup_logging():
    """Sets up basic logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # You can add file handlers or more complex configurations here
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING) # Quieten access logs if needed

# Example utility function
def format_username(first_name: str, last_name: str) -> str:
    """Formats a username."""
    return f"{first_name.capitalize()} {last_name.capitalize()}"

