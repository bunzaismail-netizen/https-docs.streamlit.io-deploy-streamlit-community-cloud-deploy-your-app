# ClimateAnalysis Test Instructions

## Running All Tests

To run all tests, open a terminal in the workspace root (`c:\Users\hp\Documents\ClimateAnalysis`) and run:

```
pytest
```

This will discover and run all tests in the `tests/` folder using the provided fixtures and monkeypatches.

## Troubleshooting
- Ensure you have all dependencies installed:
  - `pip install -r requirements.txt`
- If you see errors about missing `tkinter` or display, tests may be skipped in headless environments.
- All test files and functions use the `test_` prefix for pytest compatibility.

## Test Coverage
- GUI smoke tests: `test_gui_smoke.py`, `smoke_logout_test.py`
- Visualization logic: `test_visualization_plot.py`, `test_visualization_debounce.py`
- Tkinter root fixture: `conftest.py`

## Advanced
To run a specific test file:
```
pytest tests/test_gui_smoke.py
```

To see verbose output:
```
pytest -v
```

For more help, see [pytest documentation](https://docs.pytest.org/en/stable/).
