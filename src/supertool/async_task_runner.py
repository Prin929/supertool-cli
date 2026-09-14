import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Any, List, Optional

@dataclass
class TaskResult:
    name: str
    success: bool
    value: Any = None
    error: Optional[str] = None
    duration: float = 0.0

class TaskRunner:
    def __init__(self, max_concurrency: int = 5):
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.executor = ThreadPoolExecutor(max_workers=max_concurrency)
        self.tasks = []

    def add_task(self, name: str, func: Callable, *args, retries: int = 1, **kwargs):
        self.tasks.append({"name": name, "func": func, "args": args, "kwargs": kwargs, "retries": retries})

    async def _execute_task(self, task_info: dict) -> TaskResult:
        async with self.semaphore:
            start_time = time.perf_counter()
            retries = task_info["retries"]
            loop = asyncio.get_running_loop()
            
            for attempt in range(retries + 1):
                try:
                    res = await loop.run_in_executor(
                        self.executor,
                        lambda: task_info["func"](*task_info["args"], **task_info["kwargs"])
                    )
                    duration = time.perf_counter() - start_time
                    return TaskResult(name=task_info["name"], success=True, value=res, duration=duration)
                except Exception as exc:
                    if attempt == retries:
                        duration = time.perf_counter() - start_time
                        return TaskResult(name=task_info["name"], success=False, error=str(exc), duration=duration)

    async def run_async(self) -> List[TaskResult]:
        coroutines = [self._execute_task(t) for t in self.tasks]
        return await asyncio.gather(*coroutines)

    def run_sync(self) -> List[TaskResult]:
        return asyncio.run(self.run_async())
