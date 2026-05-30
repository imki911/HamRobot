import numpy as np

from hamrobot.utils.audio import add_silence, duration_seconds, normalize_mono_int16, rms_int16


def test_rms_int16():
    data = np.array([1000, -1000], dtype=np.int16)
    assert 999 <= rms_int16(data) <= 1001


def test_add_silence_duration():
    sr = 16000
    data = np.ones(sr, dtype=np.int16)
    out = add_silence(data, sr, head_ms=500, tail_ms=500)
    assert len(out) == sr * 2
    assert duration_seconds(out, sr) == 2.0


def test_normalize_float():
    data = np.array([0.0, 1.0, -1.0], dtype=np.float32)
    out = normalize_mono_int16(data)
    assert out.dtype == np.int16
    assert out[1] == 32767
