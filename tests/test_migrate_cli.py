import migrate_csv_to_pg


def test_migrate_cli_help_does_not_execute_migration(capsys, monkeypatch):
    called = False

    def fake_migrate(csv_path):
        nonlocal called
        called = True
        return True

    monkeypatch.setattr(migrate_csv_to_pg, "migrate", fake_migrate)

    try:
        migrate_csv_to_pg.main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0

    captured = capsys.readouterr()
    assert "Sincroniza el CSV consolidado" in captured.out
    assert called is False


def test_migrate_cli_without_run_does_not_execute_migration(monkeypatch):
    called = False

    def fake_migrate(csv_path):
        nonlocal called
        called = True
        return True

    monkeypatch.setattr(migrate_csv_to_pg, "migrate", fake_migrate)

    exit_code = migrate_csv_to_pg.main([])

    assert exit_code == 2
    assert called is False


def test_migrate_cli_requires_explicit_yes(monkeypatch):
    called = False

    def fake_migrate(csv_path):
        nonlocal called
        called = True
        return True

    monkeypatch.setattr(migrate_csv_to_pg, "migrate", fake_migrate)

    exit_code = migrate_csv_to_pg.main(["--run"])

    assert exit_code == 2
    assert called is False


def test_migrate_cli_runs_only_with_run_and_yes(monkeypatch):
    received_csv_path = None

    def fake_migrate(csv_path):
        nonlocal received_csv_path
        received_csv_path = csv_path
        return True

    monkeypatch.setattr(migrate_csv_to_pg, "migrate", fake_migrate)

    exit_code = migrate_csv_to_pg.main(["--run", "--yes", "--csv-path", "custom.csv"])

    assert exit_code == 0
    assert received_csv_path == "custom.csv"
