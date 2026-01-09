import os
import time
from locust import HttpUser, between, task


BOT_BASE_PATH = os.getenv("BOT_BASE_PATH", "/bot")


class BotLoadUser(HttpUser):
    wait_time = between(0.1, 0.5)

    @task(3)
    def start_command(self) -> None:
        with self.client.post(
            f"{BOT_BASE_PATH}/start",
            json={"user_id": self.user_id, "command": "/start"},
            catch_response=True,
        ) as response:
            if response.elapsed.total_seconds() > 2:
                response.failure("Latency > 2s")

    @task(1)
    def status_command(self) -> None:
        with self.client.post(
            f"{BOT_BASE_PATH}/status",
            json={"user_id": self.user_id, "command": "/status"},
            catch_response=True,
        ) as response:
            if response.elapsed.total_seconds() > 2:
                response.failure("Latency > 2s")

    @task(2)
    def buy_command(self) -> None:
        with self.client.post(
            f"{BOT_BASE_PATH}/buy",
            json={"user_id": self.user_id, "command": "/buy"},
            catch_response=True,
        ) as response:
            if response.elapsed.total_seconds() > 2:
                response.failure("Latency > 2s")

    @task(1)
    def payment_race(self) -> None:
        with self.client.post(
            f"{BOT_BASE_PATH}/pay",
            json={"user_id": self.user_id, "command": "/pay"},
            catch_response=True,
        ) as response:
            if response.elapsed.total_seconds() > 2:
                response.failure("Latency > 2s")

    def on_start(self) -> None:
        self.user_id = int(time.time() * 1000) % 1000000
