import functools
import logging
import logging.handlers
import time


def log_calls(
    logger: logging.Logger | None = None,
    level: int = logging.DEBUG,
    log_args: bool = True,
    log_result: bool = True,
    log_time: bool = True,
    max_repr_len: int = 200,
):
    """ Декоратор для логирования вызовов функций """
    def decorator(func):
        func_name = func.__qualname__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _logger = logger or logging.getLogger()

            if log_args:
                args_for_log = args[1:] if args and hasattr(args[0], func.__name__) else args
                args_str = _short_repr(args_for_log, max_repr_len)
                kwargs_str = _short_repr(kwargs, max_repr_len) if kwargs else ''
                if kwargs_str:
                    _logger.log(level, "→ %s(%s, **%s)", func_name, args_str, kwargs_str)
                else:
                    _logger.log(level, "→ %s(%s)", func_name, args_str)
            else:
                _logger.log(level, "→ %s()", func_name)

            start = time.time()

            try:
                result = func(*args, **kwargs)
            except Exception as e:
                elapsed = time.time() - start
                _logger.exception(
                    "✗ %s упал%s: %s",
                    func_name,
                    f" ({elapsed:.3f} сек)" if log_time else "",
                    e,
                )
                raise

            elapsed = time.time() - start

            if log_result:
                result_str = _short_repr(result, max_repr_len)
            else:
                result_str = '<skipped>'

            if log_time:
                _logger.log(level, "← %s = %s (%.3f сек)", func_name, result_str, elapsed)
            else:
                _logger.log(level, "← %s = %s", func_name, result_str)

            return result

        return wrapper
    return decorator


def _short_repr(value, max_len: int = 200) -> str:
    """ Обрезает длинные строки/объекты """
    try:
        s = repr(value)
    except Exception:
        s = f"<unrepr {type(value).__name__}>"
    if len(s) > max_len:
        s = s[:max_len] + f"... ({len(s)} симв.)"
    return s