from amonhen.theme import (
    TURNING_VERBS,
    format_score_bar,
    get_turning_verb,
    is_color_disabled,
    render_banner,
)


def test_render_banner_contains_title_and_tagline():
    banner = render_banner(model_id="mobileclip2-s2", videos_count=5, plain=False)
    assert "Amon Hen" in banner
    assert "Seat of Seeing" in banner
    assert "MOBILECLIP2-S2" in banner


def test_render_banner_plain_mode():
    banner = render_banner(model_id="mobileclip2-s2", videos_count=5, plain=True)
    assert "Amon Hen" in banner
    assert "\033[" not in banner  # No ANSI escapes in plain mode


def test_render_banner_color_mode(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    banner = render_banner(model_id="mobileclip2-s2", videos_count=3, plain=False)
    assert "\033[38;2;240;243;248m" in banner
    assert "\033[38;2;130;170;255m" in banner
    assert "Amon Hen" in banner


def test_format_score_bar():
    bar = format_score_bar(0.5, width=10)
    assert len(bar) == 10
    assert "█" in bar
    assert "░" in bar

    bar_zero = format_score_bar(-0.5, width=8)
    assert bar_zero == "░" * 8

    bar_full = format_score_bar(1.5, width=8)
    assert bar_full == "█" * 8


def test_get_turning_verb():
    verb = get_turning_verb(seed=42)
    assert isinstance(verb, str)
    assert verb in TURNING_VERBS

    verb_random = get_turning_verb()
    assert verb_random in TURNING_VERBS


def test_is_color_disabled_respects_env(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    assert is_color_disabled() is True

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    assert is_color_disabled() is False

    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    assert is_color_disabled() is True
