"""One-shot Tk callback diagnostic helper.

Install by assigning Tk.report_callback_exception = install_reporter(tk_root)
This will capture the first background callback exception into a log file and then
restore the original handler to avoid noisy repeated prints.
"""
import traceback
import threading

_LOG_PATH = "tk_bgerror.log"
_lock = threading.Lock()


def install_reporter(root):
    orig = getattr(root, 'report_callback_exception', None)

    def reporter(exc, val, tb):
        # Write a single detailed trace to a file; avoid flooding the console
        with _lock:
            try:
                with open(_LOG_PATH, 'a', encoding='utf-8') as f:
                    f.write('--- Tk background callback exception ---\n')
                    traceback.print_exception(exc, val, tb, file=f)
                    f.write('\n')
            except Exception:
                pass
        # restore original handler to keep behaviour stable
        try:
            if orig:
                setattr(root, 'report_callback_exception', orig)
        except Exception:
            pass

    return reporter
