from app import info_response, menu_keyboard


def test_info_response_preserves_legacy_readme_privacy_terms():
    assert "Do i need a vpn" in info_response("Read me")
    assert "We don't store your data" in info_response("Privacy Policy")
    assert "We are not responsible" in info_response("Terms")


def test_menu_keyboard_contains_legacy_info_buttons():
    labels = [button.text for row in menu_keyboard().keyboard for button in row]

    assert "Read me" in labels
    assert "Privacy Policy" in labels
    assert "Terms" in labels
    assert "Search" in labels
