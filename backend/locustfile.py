from locust import HttpUser, task, between
import random

class StudentUser(HttpUser):
    wait_time = between(1, 5)
    
    def on_start(self):
        # We would normally login here, but since we are just doing a simple load test
        # against a few endpoints, we can mock auth or assume endpoints that don't need auth,
        # or we can login with a test user if it exists.
        self.client.headers.update({"X-Forwarded-For": f"10.0.0.{random.randint(1, 255)}"})

    @task(3)
    def view_dashboard(self):
        # We simulate the load by hitting the health check and maybe login endpoint
        # to test concurrency and caching
        self.client.get("/api/v1/health")

    @task(1)
    def test_login(self):
        # We use a random email to avoid rate limit/cache hits that bypass the logic
        self.client.post("/api/v1/auth/login", json={
            "email": f"student{random.randint(1,100)}@school.com",
            "password": "wrongpassword"
        })
