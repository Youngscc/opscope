"""Mount this router with a host-owned app.state.opscope_runtime."""
import json
import re
from functools import lru_cache

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from opscope.offline.build import build_payload, render_page
from opscope.evaluation.time_comparison import compare_payload
from opscope.evaluation.html_reports import comparison_report, single_report

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


def get_job(request, job_id, since_revision=None):
    runtime = getattr(request.app.state, 'opscope_runtime', None)
    if not re.fullmatch('[a-f0-9]{32}', job_id) or runtime is None:
        return None
    return runtime.get(job_id) if since_revision is None else runtime.get(job_id, since_revision)


@router.get('/evaluations/history')
def history(request: Request):
    runtime = getattr(request.app.state, 'opscope_runtime', None)
    return runtime.history() if runtime else []


@router.get('/evaluations/compare')
def compare(request: Request, left: str, right: str):
    if left == right:
        return error('请选择两个不同的评估时间。')
    first, second = get_job(request, left), get_job(request, right)
    if not first or not second or any(job['status'] not in {'completed', 'failed'}
                                     or 'payload' not in job for job in (first, second)):
        return error('评估记录不存在、尚未完成或已过期。', 404)
    return compare_payload(first['payload'], second['payload'])


@router.get('/evaluations/compare/report')
def compare_report(request: Request, left: str, right: str):
    if left == right:
        return error('请选择两个不同的评估时间。')
    first, second = get_job(request, left), get_job(request, right)
    if not first or not second or any(job['status'] not in {'completed', 'failed'}
                                     or 'payload' not in job for job in (first, second)):
        return error('评估记录不存在、尚未完成或已过期。', 404)
    return HTMLResponse(comparison_report(first, second), headers={
        'Content-Disposition': f'attachment; filename="opscope-compare-{left[:8]}-{right[:8]}.html"'})


@router.get('/evaluations/{job_id}')
def evaluation(request: Request, job_id: str, since_revision: int | None = None):
    return get_job(request, job_id, since_revision) or error('任务不存在或已过期。', 404)


@router.get('/evaluations/{job_id}/report')
def result_report(request: Request, job_id: str, hardware: str, method: str):
    job = get_job(request, job_id)
    if not job or job['status'] not in {'completed', 'failed'} or 'payload' not in job:
        return error('评估记录不存在、尚未完成或已过期。', 404)
    row = next((item for item in job['payload']['results'] if item['hardware'] == hardware
                and item['method'] == method and item['task']['status'] != 'not_run'), None)
    if row is None:
        return error('本次任务没有这个评估结果。', 404)
    label = re.sub('[^A-Za-z0-9_-]', '_', f'{hardware}-{method}')[:70]
    return HTMLResponse(single_report(job, row), headers={
        'Content-Disposition': f'attachment; filename="opscope-result-{job_id[:8]}-{label}.html"'})


@router.get('/evaluations/{job_id}/snapshot')
def snapshot(request: Request, job_id: str):
    job = get_job(request, job_id)
    if job is None:
        return error('任务不存在或已过期。', 404)
    if job['status'] != 'completed':
        return error('结果尚未完成。', 409)
    return HTMLResponse(render_page(job['payload']), headers={
        'Content-Disposition': f'attachment; filename="opscope-{job_id}.html"'})
