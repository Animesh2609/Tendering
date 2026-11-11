"""Sample process RSS during an operation (not isolated model memory)."""
import os
import time
import threading
import psutil

_process = psutil.Process(os.getpid())

def profile_resources(function, *args, **kwargs):
    """
    Measure wall-clock runtime and process RSS memory while a function runs.
    Returns: function result and a dictionary of measurements.
    """
    memory_samples = [_process.memory_info().rss / (1024 ** 2)]
    stop_sampling = threading.Event()

    def sample_memory():
        while not stop_sampling.is_set():
            try:
                memory_samples.append(
                    _process.memory_info().rss / (1024 ** 2)
                )
            except psutil.Error:
                pass
            stop_sampling.wait(0.05)

    memory_before = _process.memory_info().rss / (1024 ** 2)
    sampler = threading.Thread(target=sample_memory, daemon=True)

    start = time.perf_counter()
    sampler.start()

    try:
        result = function(*args, **kwargs)
    finally:
        elapsed = time.perf_counter() - start
        stop_sampling.set()
        sampler.join()
        memory_after = _process.memory_info().rss / (1024 ** 2)

    measurements = {
        "runtime_seconds": round(elapsed, 3),
        "memory_before_MB": round(memory_before, 2),
        "memory_after_MB": round(memory_after, 2),
        "peak_process_memory_MB": round(max(memory_samples), 2),
        "peak_increase_from_start_MB": round(
            max(memory_samples) - memory_before, 2
        ),
    }

    return result, measurements
