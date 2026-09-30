import pytest
import py_compile

def test_app_syntax():
    """app.py 파일의 문법적 오류가 없는지 컴파일 테스트를 수행합니다."""
    res = py_compile.compile("app.py", doraise=True)
    assert res is not None
