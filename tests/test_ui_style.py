from cv_manager.ui_style import apply_styles, card, create_card_html


def test_apply_styles(mocker):
    # Mock st.markdown
    mock_markdown = mocker.patch("streamlit.markdown")
    apply_styles()

    # Assert st.markdown was called with CSS
    mock_markdown.assert_called_once()
    args, kwargs = mock_markdown.call_args
    assert kwargs.get("unsafe_allow_html") is True
    assert "<style>" in args[0]
    assert "background-color: #F5F5F7;" in args[0]
    assert ".apple-card" in args[0]


def test_card(mocker):
    mock_markdown = mocker.patch("streamlit.markdown")
    card("Test Title", "<p>Test Content</p>")

    # Assert st.markdown was called with generated HTML
    mock_markdown.assert_called_once()
    args, kwargs = mock_markdown.call_args
    assert kwargs.get("unsafe_allow_html") is True
    assert '<div class="apple-card">' in args[0]
    assert "<h3>Test Title</h3>" in args[0]
    assert "<div><p>Test Content</p></div>" in args[0]


def test_create_card_html():
    html = create_card_html("Test Title 2", "<p>Content 2</p>")

    assert '<div class="apple-card">' in html
    assert "<h3>Test Title 2</h3>" in html
    assert "<div><p>Content 2</p></div>" in html
