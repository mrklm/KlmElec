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
