"""Load testing with Locust."""

from locust import HttpUser, between, task


class ComplianceGuardUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "loadtest@example.com",
                "password": "SecureP@ssw0rd!99",
            },
        )
        if response.status_code == 200:
            self.token = response.json().get("access_token", "")
        else:
            self.token = ""

    @task(3)
    def health(self):
        self.client.get("/health")

    @task(2)
    def list_scans(self):
        if self.token:
            self.client.get(
                "/api/v1/scans",
                headers={"Authorization": f"Bearer {self.token}"},
            )

    @task(1)
    def get_me(self):
        if self.token:
            self.client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {self.token}"},
            )
