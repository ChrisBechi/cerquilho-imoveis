from app.config.settings import CHECK_INTERVAL_MINUTES

def test_check_interval():
    assert CHECK_INTERVAL_MINUTES == 30