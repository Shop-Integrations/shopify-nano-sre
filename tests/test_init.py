"""Tests for initialization modules."""


def test_agent_init():
    """Test agent module initialization."""
    from nano_sre.agent import __init__ as agent_module

    assert agent_module is not None


def test_config_init():
    """Test config module initialization."""
    from nano_sre.config import __init__ as config_module

    assert config_module is not None


def test_db_init():
    """Test database module initialization."""
    from nano_sre.db import __init__ as db_module

    assert db_module is not None


def test_main_init():
    """Test main nano_sre module initialization."""
    import nano_sre

    assert nano_sre is not None
