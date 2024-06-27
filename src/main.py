import os

import psycopg2
from signalrcore.hub_connection_builder import HubConnectionBuilder
import logging
import requests
import json
import time


class App:
    def __init__(self):
        self._hub_connection = None
        self.TICKS = 10

        # To be configured by your team
        self.HOST = os.getenv('HOST')  # Setup your host here
        self.TOKEN = os.getenv('TOKEN')  # Setup your token here
        self.T_MAX = os.getenv('T_MAX')  # Setup your max temperature here
        self.T_MIN = os.getenv('T_MIN')  # Setup your min temperature here
        #self.DATABASE_URL = os.getenv('')  # Setup your database here
        try:
            self.connection = psycopg2.connect(
                host=os.getenv('DB_HOST'),
                database=os.getenv('DB_NAME'),
                user=os.getenv('DB_USER'),
                password=os.getenv('DB_PASSWORD'),
                port=os.getenv('DB_PORT')
            )
        except psycopg2.Error as e:
            print("Error connecting to the database: ", e)

    def __del__(self):
        if self._hub_connection != None:
            self._hub_connection.stop()

    def start(self):
        """Start Oxygen CS."""
        self.setup_sensor_hub()
        self._hub_connection.start()
        print("Press CTRL+C to exit.")
        while True:
            time.sleep(2)

    def setup_sensor_hub(self):
        """Configure hub connection and subscribe to sensor data events."""
        self._hub_connection = (
            HubConnectionBuilder()
            .with_url(f"{self.HOST}/SensorHub?token={self.TOKEN}")
            .configure_logging(logging.INFO)
            .with_automatic_reconnect(
                {
                    "type": "raw",
                    "keep_alive_interval": 10,
                    "reconnect_interval": 5,
                    "max_attempts": 999,
                }
            )
            .build()
        )
        self._hub_connection.on("ReceiveSensorData", self.on_sensor_data_received)
        self._hub_connection.on_open(lambda: print("||| Connection opened."))
        self._hub_connection.on_close(lambda: print("||| Connection closed."))
        self._hub_connection.on_error(
            lambda data: print(f"||| An exception was thrown closed: {data.error}")
        )

    def on_sensor_data_received(self, data):
        """Callback method to handle sensor data on reception."""
        try:
            print(data[0])
            print(data[0]["date"] + " --> " + data[0]["data"], flush=True)
            timestamp = data[0]["date"]
            temperature = float(data[0]["data"])
            etat = self.take_action(temperature)
            self.save_event_to_database(timestamp, temperature,etat)
        except Exception as err:
            print(err)

    def take_action(self, temperature):
        """Take action to HVAC depending on current temperature."""
        if float(temperature) >= float(self.T_MAX):
            return self.send_action_to_hvac("TurnOnAc")
        elif float(temperature) <= float(self.T_MIN):
            return self.send_action_to_hvac("TurnOnHeater")

    def send_action_to_hvac(self, action):
        """Send action query to the HVAC service."""
        r = requests.get(f"{self.HOST}/api/hvac/{self.TOKEN}/{action}/{self.TICKS}")
        details = json.loads(r.text)
        print(details, flush=True)
        return details["Response"]

    def save_event_to_database(self, timestamp, temperature,etat):
        """Save sensor data into database."""
        try:
            cur = self.connection.cursor()
            cur.execute("INSERT INTO sensor (temperature, heure, etat) VALUES (%s, %s, %s) ON CONFLICT (id) DO NOTHING", (temperature, timestamp, etat))
            self.connection.commit()
            cur.close()
            pass
        except requests.exceptions.RequestException as e:
            # To implement
            pass


if __name__ == "__main__":
    app = App()
    app.start()
