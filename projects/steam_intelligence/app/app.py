"""Streamlit entry point for the Steam Intelligence app."""

from pathlib import Path

import streamlit as st

PROJECT_NAME: str = "Steam Intelligence"
GITHUB_URL: str = "https://github.com/bona1204/Portafolio/tree/main/projects/steam_intelligence"
DEMO_URL: str = "https://huggingface.co/spaces/SebastianZapata/steam_intelligence"


def render_sidebar() -> None:
    """Render the sidebar with project branding and navigation."""
    with st.sidebar:
        st.title(PROJECT_NAME)
        st.caption("Data Engineering Portfolio")
        # TODO: add navigation links to app/pages/ once built


def render_home() -> None:
    """Render the home page with a description of the project."""
    st.header(PROJECT_NAME)
    st.write("Description of the project goes here.")
    # TODO: add project overview, key metrics, and charts


def render_footer() -> None:
    """Render the footer with links to the GitHub repo and live demo."""
    st.divider()
    st.markdown(f"[GitHub]({GITHUB_URL}) · [Demo]({DEMO_URL})")


def main() -> None:
    """Configure the page and render all sections."""
    st.set_page_config(layout="wide", page_title=PROJECT_NAME)
    render_sidebar()
    render_home()
    render_footer()


if __name__ == "__main__":
    main()
