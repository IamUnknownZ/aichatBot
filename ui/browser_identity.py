from pathlib import Path
import streamlit as st
import streamlit.components.v2 as components
from rag.chat_history import _owner

_component_js = Path(__file__).with_suffix('.mjs').read_text()


def normalize_identity(value):
    if not isinstance(value, dict):
        return None
    try:
        _owner(value.get('token'))
    except ValueError:
        return None
    return {'token': value['token'], 'persisted': value.get('persisted') is True}


def browser_identity():
    component = components.component(
        'anonymous_browser_identity',
        js=_component_js,
    )
    current = normalize_identity(st.session_state.get('browser_identity'))
    result = component(key='anonymous_owner', data={'identity': current},
                       default={'identity': None}, height=0,
                       on_identity_change=lambda: None)
    value = normalize_identity(result.identity)
    if value:
        st.session_state['browser_identity'] = value
        return value
    return current
