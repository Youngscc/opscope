"""Compatibility launcher for the FastAPI application; prefer ./start.sh."""
if __name__ == '__main__':
    from backend.web.__main__ import main
    main()
