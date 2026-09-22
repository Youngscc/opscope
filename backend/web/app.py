"""Standalone FastAPI host; routes can also be included in modeling."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from opscope.evaluation.evaluation_runtime import EvaluationRuntime
from .routes.opscope import router
from .settings import Settings


def create_app(settings=None, runtime=None):
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        owned = runtime is None and settings.engine_root and settings.engine_python
        if owned:
            app.state.opscope_runtime = await run_in_threadpool(
                EvaluationRuntime, settings.engine_root, settings.engine_python,
                tilesim_python=settings.tilesim_python or None)
        try:
            yield
        finally:
            if owned:
                await run_in_threadpool(app.state.opscope_runtime.close)

    app = FastAPI(title='OpScope API', lifespan=lifespan)
    app.state.opscope_runtime = runtime
    app.include_router(router)
    install_local_guard(app, settings)
    install_frontend(app, settings.frontend_dist)
    return app


def install_local_guard(app, settings):
    @app.middleware('http')
    async def local_guard(request: Request, call_next):
        origin = request.headers.get('origin')
        host = request.headers.get('host')
        hosts = {f'{name}:{settings.port}' for name in ('localhost', '127.0.0.1')}
        if host not in hosts or (origin and origin not in settings.origins):
            return JSONResponse({'error': '请从本地服务页面访问。'}, status_code=403)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Cache-Control'] = 'no-store'
        return response


def install_frontend(app, directory):
    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'service': 'opscope'}

    @app.get('/{path:path}', include_in_schema=False)
    def frontend(path: str):
        if path.startswith(('api/', 'docs/', 'openapi.')):
            return JSONResponse({'error': '未知接口。'}, status_code=404)
        target = (directory / path).resolve()
        if not target.is_relative_to(directory.resolve()):
            return JSONResponse({'error': '未知资源。'}, status_code=404)
        if target.is_file():
            return FileResponse(target)
        if path not in ('', 'index.html', 'opscope', 'opscope/'):
            return JSONResponse({'error': '未知页面或资源。'}, status_code=404)
        page = directory / 'index.html'
        if not page.exists():
            return JSONResponse({'error': '请先运行 npm --prefix frontend run build。'}, status_code=503)
        return FileResponse(page)
