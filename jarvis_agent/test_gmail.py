import unittest
from unittest.mock import MagicMock, patch
import os
import sys

# Ensure jarvis_agent is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools import read_latest_emails, send_email, get_gmail_service

class TestGmailAPI(unittest.TestCase):

    @patch("tools.os.path.exists")
    def test_missing_credentials(self, mock_exists):
        mock_exists.return_value = False
        result = read_latest_emails()
        self.assertIn("Erro: Credenciais da API do Gmail não configuradas", result)

    @patch("tools.get_gmail_service")
    def test_empty_inbox(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.users().messages().list().execute.return_value = {"messages": []}

        result = read_latest_emails(3)
        self.assertEqual(result, "Nenhum e-mail encontrado na caixa de entrada.")

    @patch("tools.get_gmail_service")
    def test_read_emails_success(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}, {"id": "msg2"}]
        }

        def get_msg_side_effect(userId, id, format):
            mock_msg = MagicMock()
            if id == "msg1":
                payload = {
                    "headers": [
                        {"name": "From", "value": "alice@example.com"},
                        {"name": "Subject", "value": "Reunião de Alinhamento"},
                    ]
                }
                snippet = "Olá, vamos alinhar o projeto."
            else:
                payload = {
                    "headers": [
                        {"name": "From", "value": "bob@example.com"},
                        {"name": "Subject", "value": "Relatório Semanal"},
                    ]
                }
                snippet = "Segue o relatório em anexo."
            mock_msg.execute.return_value = {"payload": payload, "snippet": snippet}
            return mock_msg

        mock_service.users().messages().get.side_effect = get_msg_side_effect

        result = read_latest_emails(2)
        self.assertIn("De: alice@example.com | Assunto: Reunião de Alinhamento | Trecho: Olá, vamos alinhar o projeto.", result)
        self.assertIn("De: bob@example.com | Assunto: Relatório Semanal | Trecho: Segue o relatório em anexo.", result)

    @patch("tools.get_gmail_service")
    def test_read_emails_exception_handling(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.users().messages().list().execute.side_effect = Exception("API rate limit exceeded")

        result = read_latest_emails(3)
        self.assertEqual(result, "Erro ao ler e-mails via Gmail API: API rate limit exceeded")

    @patch("tools.get_gmail_service")
    def test_send_email_success_gmail_api(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        result = send_email("test@example.com", "Assunto", "Corpo do email")
        self.assertEqual(result, "E-mail enviado com sucesso para test@example.com!")
        mock_service.users().messages().send.assert_called_once()

    @patch("tools.get_gmail_service")
    def test_send_email_error_gmail_api(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.users().messages().send.side_effect = Exception("Insufficient Permission")

        result = send_email("test@example.com", "Assunto", "Corpo do email")
        self.assertIn("Erro ao enviar e-mail via Gmail API", result)
        self.assertIn("Insufficient Permission", result)


if __name__ == "__main__":
    unittest.main()
