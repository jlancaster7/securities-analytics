from securities_analytics.utils.data_imports.curves import load_and_return_active_treasury_curve


def test_treasury_curve_dict_type() -> None:
    active_treasury_curve: dict[float, float] = load_and_return_active_treasury_curve(
        file_path="tests/data/active_treasury_curve.csv"
    )
    assert isinstance(active_treasury_curve, dict)


def test_treasury_curve_not_empty() -> None:
    active_treasury_curve: dict[float, float] = load_and_return_active_treasury_curve(
        file_path="tests/data/active_treasury_curve.csv"
    )
    assert len(active_treasury_curve.keys()) > 0


if __name__ == "__main__":
    active_treasury_curve: dict[float, float] = load_and_return_active_treasury_curve(
        file_path="tests/data/active_treasury_curve.csv"
    )
    assert isinstance(active_treasury_curve, dict)
