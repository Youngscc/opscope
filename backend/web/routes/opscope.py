"""Mount this router with a host-owned app.state.opscope_runtime."""
import json
import re
from functools import lru_cache

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from build import build_payload, render_page

router = APIRouter(prefix='/api/opscope', tags=['opscope'])


def error(message, status=400):
    return JSONResponse({'error': message}, status_code=status)


@lru_cache(maxsize=1)
def bootstrap_payload():
    return build_payload()


@router.get('/bootstrap')
def bootstrap():
    return bootstrap_payload()


@router.get('/capabilities')
def capabilities(request: Request):
    runtime = getattr(request.app.state, 'opscope_runtime', None)
    return runtime.capabilities if runtime else {'ready': False, 'reason': '演示模式 · 未配置评估引擎'}


async def read_configuration(request):
    if request.headers.get('content-type', '').split(';')[0] != 'application/json':
        return None, error('仅接受 JSON 配置。', 415)
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 65536:
            return None, error('请求超过64KiB限制。', 413)
    try:
        return json.loads(body), None
    except (ValueError, UnicodeDecodeError):
        return None, error('JSON格式错误。')


@router.post('/evaluations', status_code=202)
async def submit(request: Request):
    body, invalid = await read_configuration(request)
    if invalid is not None:
        return invalid
    runtime = getattr(request.app.state, 'opscope_runtime', None)
    if runtime is None:
        return error('未配置评估引擎。', 503)
    try:
        return await run_in_threadpool(runtime.submit, body)
    except (ValueError, TypeError, KeyError, OverflowError) as exc:
        return error(str(exc) if isinstance(exc, ValueError) else '配置格式无效。')


def get_job(request, job_id):
    runtime = getattr(request.app.state, 'opscope_runtime', None)
    if not re.fullmatch('[a-f0-9]{32}', job_id) or runtime is None:
        return None
    return runtime.get(job_id)


@router.get('/evaluations/{job_id}')
def evaluation(request: Request, job_id: str):
    return get_job(request, job_id) or error('任务不存在或已过期。', 404)


@router.get('/evaluations/{job_id}/snapshot')
def snapshot(request: Request, job_id: str):
    job = get_job(request, job_id)
    if job is None:
        return error('任务不存在或已过期。', 404)
    if job['status'] != 'completed':
        return error('结果尚未完成。', 409)
    return HTMLResponse(render_page(job['payload']), headers={
        'Content-Disposition': f'attachment; filename="opscope-{job_id}.html"'})
