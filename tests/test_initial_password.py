from datetime import date

import pytest

from app.api.auth import generate_initial_password


@pytest.mark.parametrize(
    ("first_name", "date_of_birth", "expected"),
    [
        ("Kalyan", date(1990, 1, 1), "KAL01011990yan"),
        ("John", date(1988, 12, 20), "JOH12201988n"),
        ("Al", date(2000, 6, 5), "AL06052000"),
        ("Mary Jane", date(1995, 3, 9), "MAR03091995yjane"),
    ],
)
def test_generate_initial_password(first_name, date_of_birth, expected):
    assert generate_initial_password(first_name, date_of_birth) == expected


def test_generate_initial_password_rejects_name_without_letters():
    with pytest.raises(ValueError, match="must contain letters"):
        generate_initial_password("---", date(1990, 1, 1))
