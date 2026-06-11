from app.services.nutrition_targets import calculate_fiber_bounds, calculate_target_fiber_g


def test_fiber_for_male_under_50_high_calories():
    bounds = calculate_fiber_bounds(3379, "male", 40)

    assert bounds["fiber_by_calories"] == 47.3
    assert bounds["base"] == 38.0
    assert bounds["min_fiber"] == 30.0
    assert bounds["max_fiber"] == 45.0
    assert bounds["target"] == 45.0
    assert calculate_target_fiber_g(3379, "male", 40) == 30.0


def test_fiber_for_male_over_50():
    bounds = calculate_fiber_bounds(2500, "male", 55)

    assert bounds["min_fiber"] == 25.0
    assert bounds["max_fiber"] == 38.0
    assert bounds["target"] == 35.0
    assert calculate_target_fiber_g(2500, "male", 55) == 25.0


def test_fiber_for_female_under_50():
    bounds = calculate_fiber_bounds(2000, "female", 35)

    assert bounds["min_fiber"] == 22.0
    assert bounds["max_fiber"] == 35.0
    assert bounds["target"] == 28.0
    assert calculate_target_fiber_g(2000, "female", 35) == 22.0


def test_fiber_for_female_over_50():
    bounds = calculate_fiber_bounds(1800, "female", 55)

    assert bounds["min_fiber"] == 20.0
    assert bounds["max_fiber"] == 30.0
    assert bounds["target"] == 25.2
    assert calculate_target_fiber_g(1800, "female", 55) == 20.0


def test_fiber_supports_russian_sex_values():
    assert calculate_target_fiber_g(3379, "мужской", 40) == 30.0
    assert calculate_target_fiber_g(2000, "женский", 35) == 22.0
