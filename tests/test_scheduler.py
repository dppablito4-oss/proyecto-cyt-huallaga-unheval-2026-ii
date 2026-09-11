import pytest

from app.vision.scheduler import MonotonicRateLimiter


def test_rate_limiter_uses_elapsed_time_instead_of_frame_count():
    limiter = MonotonicRateLimiter(fps=10)

    assert limiter.is_due(now=100.0) is True
    assert limiter.is_due(now=100.05) is False
    assert limiter.is_due(now=100.099) is False
    assert limiter.is_due(now=100.101) is True


def test_rate_limiter_reset_and_validation():
    limiter = MonotonicRateLimiter(fps=5)
    assert limiter.is_due(now=1.0) is True
    assert limiter.is_due(now=1.1) is False

    limiter.reset()

    assert limiter.is_due(now=1.1) is True
    with pytest.raises(ValueError, match="mayor que cero"):
        MonotonicRateLimiter(fps=0)
