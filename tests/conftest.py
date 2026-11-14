import pytest
from PySide6.QtWidgets import QMessageBox


@pytest.fixture(autouse=True)
def dismiss_close_prompts(monkeypatch):
    original = QMessageBox.question

    def question(parent, title, *args):
        if title == 'Enregistrer avant de quitter':
            return QMessageBox.No
        if title == 'Quitter sans enregistrer':
            return QMessageBox.Yes
        return original(parent, title, *args)

    monkeypatch.setattr(QMessageBox, 'question', question)


@pytest.fixture(autouse=True)
def no_network_from_window(monkeypatch):
    # Les comparaisons lancées par l'interface ne doivent jamais joindre les vrais sites.
    from klmelec import comparison_ui
    monkeypatch.setattr(comparison_ui, 'compare', lambda *args, **kwargs: [])
