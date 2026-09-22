"""Read flushed worker events without waiting for process exit."""
import json
from queue import Empty, Queue
import subprocess
import tempfile
from threading import Thread
import time


def read_lines(pipe, queue):
    try:
        for line in pipe:
            queue.put(line)
    finally:
        queue.put(None)


def stream_worker(command, request, context, on_row):
    timeout, directory, env = context
    deadline = time.monotonic() + timeout
    with tempfile.TemporaryFile(mode='w+') as errors:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=errors, text=True, cwd=directory, env=env)
        queue = Queue()
        reader = Thread(target=read_lines, args=(process.stdout, queue), daemon=True)
        reader.start()
        try:
            process.stdin.write(json.dumps({**request, '_stream': True}))
            process.stdin.close()
            done = False
            while True:
                try:
                    line = queue.get(timeout=max(0, deadline - time.monotonic()))
                except Empty:
                    raise subprocess.TimeoutExpired(command, timeout)
                if line is None:
                    break
                event = json.loads(line)
                if 'row' in event:
                    on_row(event['row'])
                done = done or event.get('done', False)
            code = process.wait(timeout=max(0, deadline - time.monotonic()))
            if code or not done:
                raise ValueError('评估进程未完整返回结果')
        finally:
            if process.poll() is None:
                process.kill()
            process.wait()
            process.stdin.close()
            reader.join()
            process.stdout.close()
