import asyncio
import pytest

valid_dto_is_alive = {'url':'http://127.0.0.1:5000'}

"""
namedTuple: 
c2_dto = ()
"""

@pytest.mark.parametrize("test_input,expected", [("3+5", 8), ("2+4", 6), ("6*9", 42)])
@pytest.mark.asyncio
async def test_is_alive(test_input, expected):
    assert eval(test_input) == expected