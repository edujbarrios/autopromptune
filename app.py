"""
app.py — AutoPromTune Streamlit Web Interface
=============================================
Run with:  streamlit run app.py

Part of MSc AI thesis research — Eduardo J. Barrios (@edujbarrios)
"""

import logging
import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from autopromptune import PromptTuner
from autopromptune.llm_client import LLMClient

logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AutoPromTune",
    page_icon="🔧",
    layout="centered",
)

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🔧 AutoPromTune")
st.caption(
    "LLM-powered prompt disambiguation • "
    "[GitHub @edujbarrios](https://github.com/edujbarrios) • "
    "MSc AI thesis research"
)
st.markdown(
    """
AutoPromTune identifies **vague or underspecified terms** in your prompt and
rewrites it with precise, semantically rich descriptions — making your prompts
work better with any language or vision-language model.
"""
)

st.divider()

# ---------------------------------------------------------------------------
# Sidebar — settings
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")

    api_key = st.text_input(
        "llm7.io API key",
        value=os.getenv("LLM_API_KEY", "unused"),
        type="password",
        help="llm7.io accepts any non-empty string. The default 'unused' works.",
    )
    base_url = st.text_input(
        "API base URL",
        value=os.getenv("LLM_API_BASE_URL", "https://api.llm7.io/v1"),
    )
    model = st.text_input(
        "Model",
        value=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        help="Any model supported by the endpoint.",
    )
    max_retries = st.slider("Max retries", 1, 5, 3)

    st.divider()
    st.markdown(
        "**About**\n\n"
        "AutoPromTune is part of the MSc thesis research "
        "*'Automated Prompt Engineering via Semantic Decomposition'* "
        "by Eduardo J. Barrios."
    )

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
example_prompts = [
    "Describe if there is a blue ball on the image",
    "Check if the animal is near the thing on the left",
    "Tell me if the object looks old",
    "Is the person doing an activity outside?",
]

col1, col2 = st.columns([3, 1])
with col1:
    prompt_input = st.text_area(
        "Enter your prompt",
        height=120,
        placeholder="e.g. Describe if there is a blue ball on the image",
    )
with col2:
    st.markdown("**Quick examples**")
    for ex in example_prompts:
        if st.button(ex[:40] + "…" if len(ex) > 40 else ex, key=ex, use_container_width=True):
            st.session_state["loaded_example"] = ex

# Handle example selection
if "loaded_example" in st.session_state:
    prompt_input = st.session_state.pop("loaded_example")

tune_btn = st.button("✨ Tune Prompt", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Tuning logic
# ---------------------------------------------------------------------------
if tune_btn:
    if not prompt_input.strip():
        st.warning("Please enter a prompt first.")
    else:
        with st.spinner("Running two-pass LLM analysis …"):
            try:
                client = LLMClient(
                    api_key=api_key,
                    base_url=base_url,
                    model=model,
                    max_retries=max_retries,
                )
                tuner = PromptTuner(client=client)
                result = tuner.tune(prompt_input.strip())
            except Exception as exc:
                st.error(f"Error communicating with the LLM: {exc}")
                st.stop()

        st.success("Done!")
        st.divider()

        # --- Tuned prompt ---
        st.subheader("✅ Tuned Prompt")
        st.code(result.tuned_prompt, language=None)

        col_copy, _ = st.columns([1, 3])
        with col_copy:
            st.download_button(
                "⬇️ Download",
                data=result.tuned_prompt,
                file_name="tuned_prompt.txt",
                mime="text/plain",
            )

        st.divider()

        # --- Vague terms breakdown ---
        if result.vague_terms:
            st.subheader(f"🔍 {len(result.vague_terms)} Vague Term(s) Identified")
            for i, vt in enumerate(result.vague_terms, 1):
                with st.expander(f'{i}. "{vt.term}" → "{vt.replacement}"'):
                    st.markdown(f"**Original term:** `{vt.term}`")
                    st.markdown(f"**Replacement:** `{vt.replacement}`")
                    st.markdown(f"**Reason:** {vt.reason}")
        else:
            st.info("No vague terms found — your prompt was already precise!")

        # --- Side-by-side comparison ---
        st.divider()
        st.subheader("📊 Side-by-Side Comparison")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Original**")
            st.text_area("", value=result.original_prompt, height=150, disabled=True, key="orig_display")
        with c2:
            st.markdown("**Tuned**")
            st.text_area("", value=result.tuned_prompt, height=150, disabled=True, key="tuned_display")
