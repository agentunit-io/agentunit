"""Minimal demo invoker — calls a running Agent Unit's /run endpoint.

This is NOT an Agent management platform. Lifecycle, orchestration,
and multi-unit coordination are HA-OOS responsibilities.
"""

from __future__ import annotations

import json
from urllib.parse import urlparse

import requests
import streamlit as st

_MAX_INPUT_FIELDS = 20


def _validate_url(url: str) -> str | None:
    """Return error message if URL is invalid, None if safe."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return f"URL must use http or https, got '{parsed.scheme}'"
    if not parsed.hostname:
        return "URL has no hostname"
    return None


st.set_page_config(page_title="AgentUnit Invoker", page_icon="🤖", layout="wide")
st.title("AgentUnit Invoker")

# --- Sidebar: Unit connection ---
with st.sidebar:
    st.header("Unit Connection")
    unit_url = st.text_input("Unit URL", value="http://localhost:8091").rstrip("/")

    spec: dict | None = None
    if st.button("Connect", use_container_width=True):
        url_err = _validate_url(unit_url)
        if url_err:
            st.error(url_err)
        else:
            with st.spinner("Fetching spec..."):
                try:
                    resp = requests.get(f"{unit_url}/spec", timeout=5)
                    resp.raise_for_status()
                    spec = resp.json()
                    st.session_state["spec"] = spec
                    st.session_state["unit_url"] = unit_url
                except requests.ConnectionError:
                    st.error("Cannot connect. Is the Unit running?")
                except requests.HTTPError as e:
                    st.error(f"Spec request failed: {e}")
                except requests.Timeout:
                    st.error("Connection timed out.")

    # Display Unit metadata if connected
    cached_spec = st.session_state.get("spec")
    if cached_spec:
        meta = cached_spec.get("metadata", {})
        st.divider()
        st.subheader(meta.get("name", "Unknown"))
        st.caption(f"v{meta.get('version', '?')} — {meta.get('description', '')}")
        fw = cached_spec.get("runtime", {}).get("framework", "?")
        st.text(f"Framework: {fw}")

        skills = cached_spec.get("runtime", {}).get("components", {}).get("skills", [])
        if skills:
            st.write("**Skills:**")
            for s in skills:
                sid = s.get("id") or s.get("name", "?")
                desc = s.get("description", "")
                st.markdown(f"- `{sid}`{' — ' + desc if desc else ''}")

# --- Main area: invocation ---
cached_spec = st.session_state.get("spec")

if not cached_spec:
    st.info("Connect to a running Agent Unit using the sidebar.")
    st.code(
        "au pack -t my-unit:1.0.0 -s examples/prd-writer-generic/agentunit.yaml\ndocker run --rm -p 8091:8091 -e MODEL_API_KEY=... my-unit:1.0.0"
    )
    st.stop()

# Skill selection
skills = cached_spec.get("runtime", {}).get("components", {}).get("skills", [])
skill_options: list[str] = []
if skills:
    skill_options = [s.get("id") or s.get("name", "") for s in skills]

selected_skill: str | None = None
if len(skill_options) > 1:
    selected_skill = st.selectbox("Skill", options=skill_options)
elif len(skill_options) == 1:
    selected_skill = skill_options[0]
    st.info(f"Single skill: `{selected_skill}`")

# Dynamic input form
contract = cached_spec.get("contract", {})
input_props = contract.get("inputs", {}).get("properties", {})
required_fields = contract.get("inputs", {}).get("required", [])

if not input_props:
    st.warning("This Unit declares no input fields in its contract.")
    st.stop()

if len(input_props) > _MAX_INPUT_FIELDS:
    st.error(f"Contract defines too many fields ({len(input_props)} > {_MAX_INPUT_FIELDS})")
    st.stop()

input_values: dict = {}
st.subheader("Input")

for field_name, field_def in input_props.items():
    field_type = field_def.get("type", "string")
    label = field_name + (" *" if field_name in required_fields else "")
    desc = field_def.get("description", "")

    if field_type == "string":
        input_values[field_name] = st.text_area(label, help=desc)
    elif field_type == "number":
        input_values[field_name] = st.number_input(label, help=desc, format="%f")
    elif field_type == "integer":
        input_values[field_name] = st.number_input(label, help=desc, step=1)
    elif field_type == "boolean":
        input_values[field_name] = st.checkbox(label, help=desc)
    else:
        input_values[field_name] = st.text_input(label, help=desc)

# Run
unit_url = st.session_state.get("unit_url", unit_url)

if st.button("Run", type="primary", use_container_width=True):
    url_err = _validate_url(unit_url)
    if url_err:
        st.error(url_err)
    else:
        missing = [
            f for f in required_fields if f not in input_values or input_values[f] in (None, "")
        ]
        if missing:
            st.error(f"Required fields missing: {', '.join(missing)}")
        else:
            payload: dict = {k: v for k, v in input_values.items() if v not in (None, "")}
            if selected_skill:
                payload["skill_id"] = selected_skill

            with st.spinner("Running..."):
                try:
                    resp = requests.post(f"{unit_url}/run", json=payload, timeout=120)
                    resp.raise_for_status()
                    result = resp.json()
                    st.session_state["last_result"] = result
                except requests.ConnectionError:
                    st.error("Connection lost. Is the Unit still running?")
                except requests.HTTPError:
                    st.error(f"Run failed ({resp.status_code}): {resp.text[:500]}")
                except requests.Timeout:
                    st.error("Request timed out (120s).")
                except json.JSONDecodeError:
                    st.error("Unit returned invalid JSON.")

# Display results
last_result = st.session_state.get("last_result")
if last_result:
    st.divider()
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("Output")
        output = last_result.get("output", {})

        if not isinstance(output, dict):
            st.write(output)
        elif not output:
            st.caption("Empty output.")
        else:
            markdown_keys: list[str] = []
            for key, val in output.items():
                if isinstance(val, str) and "\n" in val:
                    st.markdown(f"**{key}**")
                    st.markdown(val)
                    markdown_keys.append(key)
            rest = {k: v for k, v in output.items() if k not in markdown_keys}
            if rest:
                st.json(rest)

    with col2:
        st.subheader("Telemetry")
        telemetry = last_result.get("telemetry", {})
        if telemetry:
            if "skill_id" in telemetry:
                st.metric("Skill", telemetry["skill_id"])
            if "latency_ms" in telemetry:
                st.metric("Latency", f"{telemetry['latency_ms']}ms")
            if "token_usage" in telemetry:
                tu = telemetry["token_usage"]
                st.metric("Tokens In", tu.get("input", "?"))
                st.metric("Tokens Out", tu.get("output", "?"))
            if "model_used" in telemetry:
                st.caption(f"Model: {telemetry['model_used']}")
        else:
            st.caption("No telemetry data.")
