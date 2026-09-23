"""Start the standalone FastAPI host with Uvicorn."""
import argparse
import uvicorn

from .app import create_app
from .settings import Settings


def main():
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=settings.port)
    args = parser.parse_args()
    settings.port = args.port
    uvicorn.run(create_app(settings), host='127.0.0.1', port=settings.port)


if __name__ == '__main__':
    main()
