from app.core.focus_groups import is_nmg_focus, normalize_focus_group, normalize_focus_key


def test_normalize_focus_group_mgu_alias():
    assert normalize_focus_group("mgu") == "nmg"
    assert normalize_focus_group("nmg") == "nmg"
    assert normalize_focus_group(None) == "general"


def test_normalize_focus_key_legacy_prefix():
    assert normalize_focus_key("mgu_history") == "nmg_history"
    assert normalize_focus_key("nmg_history") == "nmg_history"


def test_is_nmg_focus():
    assert is_nmg_focus("mgu")
    assert is_nmg_focus("nmg")
    assert not is_nmg_focus("math")
