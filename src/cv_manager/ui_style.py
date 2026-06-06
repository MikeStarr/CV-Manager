import streamlit as st


def apply_styles():
    """
    Injects Apple-inspired CSS styling into the Streamlit app.
    Call this function at the beginning of your app script.
    """
    css = """
    <style>
        /* Typography */
        html, body, [class*="css"] {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
                         "SF Pro Text", "Segoe UI", Roboto, Oxygen, Ubuntu,
                         Cantarell, "Open Sans", "Helvetica Neue", sans-serif;
        }

        /* Background */
        .stApp {
            background-color: #F5F5F7;
        }

        /* Headers Hierarchy */
        h1, h2, h3, h4, h5, h6 {
            font-weight: 600;
            color: #1D1D1F;
            letter-spacing: -0.01em;
            margin-bottom: 0.5rem;
            margin-top: 1rem;
        }

        h1 { font-size: 2.5rem; }
        h2 { font-size: 2rem; }
        h3 { font-size: 1.5rem; }
        p { font-size: 1rem; color: #1D1D1F; line-height: 1.5; }

        /* Cards */
        .apple-card {
            background-color: #FFFFFF;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.02);
            padding: 1.5rem;
            margin-bottom: 1.5rem;
            border: 1px solid rgba(0,0,0,0.05);
        }

        /* Buttons overrides - Note: Streamlit buttons are inside specific divs */
        div.stButton > button:first-child {
            background-color: #0071E3; /* Apple Blue */
            color: white;
            border-radius: 8px;
            border: none;
            padding: 0.5rem 1rem;
            font-weight: 500;
            font-size: 0.95rem;
            transition: all 0.2s ease-in-out;
            box-shadow: 0 2px 4px rgba(0, 113, 227, 0.2);
        }

        div.stButton > button:first-child:hover {
            background-color: #0077ED;
            box-shadow: 0 4px 8px rgba(0, 113, 227, 0.3);
            border-color: transparent;
            color: white;
        }

        div.stButton > button:first-child:active {
            background-color: #0058B0;
        }

        /* Secondary Button Style Simulation via specific class mapping
           (Streamlit uses kind="secondary" but styling is tricky) */
        /* For standard secondary buttons, we'll try to target them if Streamlit allows,
           but typically we use a white background with a gray border. */
        div[data-testid="stBaseButton-secondary"] > button {
            background-color: #FFFFFF;
            color: #1D1D1F;
            border: 1px solid #D2D2D7;
            box-shadow: none;
        }
        div[data-testid="stBaseButton-secondary"] > button:hover {
            background-color: #F5F5F7;
            border-color: #86868B;
            color: #1D1D1F;
        }

        /* Spacing & Layout */
        .block-container {
            padding-top: 3rem !important;
            padding-bottom: 3rem !important;
            max-width: 1000px !important;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def card(title: str, content: str) -> None:
    """
    Renders an Apple-styled card using HTML injection.

    Args:
        title: The title of the card.
        content: The content inside the card (can contain HTML).
    """
    html = f"""
    <div class="apple-card">
        <h3>{title}</h3>
        <div>{content}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def create_card_html(title: str, content: str) -> str:
    """
    Generates HTML for an Apple-styled card without rendering it immediately.
    Useful for embedding inside other HTML structures.
    """
    return f"""
    <div class="apple-card">
        <h3>{title}</h3>
        <div>{content}</div>
    </div>
    """
