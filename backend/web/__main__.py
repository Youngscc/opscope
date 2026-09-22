"""Start the standalone FastAPI host with Uvicorn."""
import argparse
import uvicorn

from .app import create_app
from .settings import Settings


def main():
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=settings.port)
    parser.add_argument('--engine-root', default=settings.engine_root)
    parser.add_argument('--engine-python', default=settings.engine_python)
    parser.add_argument('--tilesim-python', default=settings.tilesim_python)
    args = parser.parse_args()
    for key, value in vars(args).items():
        setattr(settings, key, value)
    uvicorn.run(create_app(settings), host='127.0.0.1', port=settings.port)


if __name__ == '__main__':
    main()
