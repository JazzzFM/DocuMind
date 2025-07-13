from locust import HttpUser, task, between
import json

class DocuMindUser(HttpUser):
    wait_time = between(1, 2)
    host = "http://localhost:8000"
    token = None

    def on_start(self):
        self.login()

    def login(self):
        response = self.client.post(
            "/api/v1/auth/token/",
            json={
                "username": "admin",
                "password": "your-password"  # Replace with your admin password
            },
            name="/api/v1/auth/token/"
        )
        if response.status_code == 200:
            self.token = response.json()["access"]
        else:
            print(f"Login failed: {response.status_code} - {response.text}")
            self.environment.runner.quit()

    @task(3)
    def process_document(self):
        if not self.token:
            self.login()
            if not self.token:
                return

        # Create a dummy PDF file for testing
        with open("dummy_invoice.pdf", "w") as f:
            f.write("This is a dummy invoice for testing.")

        with open("dummy_invoice.pdf", "rb") as f:
            files = {'file': ('dummy_invoice.pdf', f, 'application/pdf')}
            headers = {"Authorization": f"Bearer {self.token}"}
            self.client.post(
                "/api/v1/documents/process/",
                files=files,
                headers=headers,
                name="/api/v1/documents/process/"
            )
        os.remove("dummy_invoice.pdf")

    @task(1)
    def get_statistics(self):
        if not self.token:
            self.login()
            if not self.token:
                return

        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.get(
            "/api/v1/documents/statistics/",
            headers=headers,
            name="/api/v1/documents/statistics/"
        )

    @task(2)
    def search_documents(self):
        if not self.token:
            self.login()
            if not self.token:
                return

        headers = {"Authorization": f"Bearer {self.token}"}
        self.client.get(
            "/api/v1/documents/search/?query=invoice",
            headers=headers,
            name="/api/v1/documents/search/"
        )
