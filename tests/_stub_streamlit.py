"""Minimal Streamlit stub so page modules can be imported in tests.

The pages are scripts: importing one executes its whole body. This stub makes
that harmless — every widget returns a falsy dummy, nothing renders, and
st.rerun raises a catchable signal instead of stopping the interpreter.
"""

from __future__ import annotations

import sys
import types


class Rerun(Exception):
    """Raised by the stubbed st.rerun() so callers can detect a rerun."""


class _Dummy:
    def __enter__(self): return self
    def __exit__(self, *exc): return False
    def __call__(self, *args, **kwargs): return self
    def __getattr__(self, name): return _Dummy()
    def __bool__(self): return False
    def __iter__(self): return iter(())


class _SessionState(dict):
    def __getattr__(self, key): return self.get(key)
    def __setattr__(self, key, value): self[key] = value


def install() -> types.ModuleType:
    """Install the stub into sys.modules and return it."""
    st = types.ModuleType("streamlit")
    st.__path__ = []  # look like a package

    def noop(*args, **kwargs):
        return _Dummy()

    for name in (
        "set_page_config", "markdown", "title", "header", "subheader", "write", "caption",
        "text_input", "text_area", "selectbox", "multiselect", "slider", "radio", "container",
        "expander", "tabs", "sidebar", "image", "dataframe", "table", "metric", "divider",
        "switch_page", "form", "file_uploader", "number_input", "date_input", "empty",
        "spinner", "progress", "toast", "stop", "cache_data", "cache_resource",
        "download_button", "form_submit_button", "json", "code", "plotly_chart",
        "altair_chart", "line_chart", "bar_chart", "popover", "status", "html", "info",
        "warning", "error", "success", "badge", "secrets",
    ):
        setattr(st, name, noop)

    st.session_state = _SessionState()
    st.query_params = _SessionState()
    # columns/tabs are unpacked by callers, so they must yield the right count.
    st.columns = lambda spec=2, **k: [_Dummy() for _ in range(spec if isinstance(spec, int) else len(spec))]
    st.tabs = lambda labels, **k: [_Dummy() for _ in (labels or [])]

    # Input widgets must return values of the right *type*: page code does
    # arithmetic on them. Returning a dummy here produces TypeErrors that look
    # like page bugs but are really harness gaps.
    def _number_input(label=None, min_value=None, max_value=None, value=None, **k):
        if value is not None:
            return value
        if min_value is not None:
            return min_value
        return 0

    def _select(label=None, options=(), index=0, **k):
        options = list(options or [])
        if not options:
            return None
        return options[index if isinstance(index, int) and 0 <= index < len(options) else 0]

    def _text(label=None, value="", **k):
        return value if isinstance(value, str) else ""

    st.number_input = _number_input
    st.slider = _number_input
    st.selectbox = _select
    st.radio = _select
    st.text_input = _text
    st.text_area = _text
    st.multiselect = lambda *a, **k: list(k.get("default") or [])
    st.file_uploader = lambda *a, **k: []
    st.button = lambda *a, **k: False
    st.checkbox = lambda *a, **k: bool(k.get("value", False))
    st.toggle = lambda *a, **k: bool(k.get("value", False))
    st.secrets = {}

    def _rerun(*args, **kwargs):
        raise Rerun()

    st.rerun = _rerun
    st.experimental_rerun = _rerun

    components = types.ModuleType("streamlit.components")
    components.__path__ = []
    v1 = types.ModuleType("streamlit.components.v1")
    v1.html = noop
    v1.declare_component = noop
    components.v1 = v1
    st.components = components

    sys.modules["streamlit"] = st
    sys.modules["streamlit.components"] = components
    sys.modules["streamlit.components.v1"] = v1
    return st


def load_page(module_name: str, path: str):
    """Import a Streamlit page module, swallowing its script-body side effects."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except (Rerun, SystemExit):
        pass
    return module
