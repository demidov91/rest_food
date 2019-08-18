import pytest

from rest_food.states.utils import validate_phone_number
from rest_food.exceptions import ValidationError


@pytest.mark.parametrize('text', [
    '+375445360207',
    '+000000000000',
    '123456789012',
    '291239876',
    '29-123-98-76',
    '1234567',
    'My phone is 291239876',
    'My phone is:\n1234567',
    'A1:\n1234567',
    'A1: 1234567\nA2: 9876543',
])
def test_validate_phone_number__valid(text):
    assert validate_phone_number(text) is None


@pytest.mark.parametrize('text', [
    'Three two one',
    '321',
    '23-45-67',
    '1' * 101,
    '',
])
def test_validate_phone_number__invalid(text):
    with pytest.raises(ValidationError):
        validate_phone_number(text)
