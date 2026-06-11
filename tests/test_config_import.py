import importlib


def test_config_loads_from_module_path_when_cwd_changes(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    import config

    reloaded = importlib.reload(config)

    assert reloaded.CONFIG_PATH.exists()
    assert reloaded.CONFIG_PATH.name == "config.yaml"
    assert reloaded.CONFIG_PATH.parent == reloaded.BASE_DIR
    assert reloaded.ESTADOS_MX
