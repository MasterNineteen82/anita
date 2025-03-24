import paho.mqtt.client as mqtt

class MQTTManager:
    def __init__(self, broker, port, client_id, username=None, password=None):
        self.broker = broker
        self.port = port
        self.client_id = client_id
        self.username = username
        self.password = password
        self.client = mqtt.Client(client_id)

        if username and password:
            self.client.username_pw_set(username, password)

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

    def connect(self):
        self.client.connect(self.broker, self.port, 60)
        self.client.loop_start()

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected with result code {rc}")

    def on_message(self, client, userdata, msg):
        print(f"Message received: {msg.topic} {msg.payload}")

    def on_disconnect(self, client, userdata, rc):
        print(f"Disconnected with result code {rc}")

    def subscribe(self, topic):
        self.client.subscribe(topic)

    def publish(self, topic, payload):
        self.client.publish(topic, payload)

# Example usage
if __name__ == "__main__":
    mqtt_manager = MQTTManager(broker="mqtt.example.com", port=1883, client_id="example_client")
    mqtt_manager.connect()
    mqtt_manager.subscribe("test/topic")
    mqtt_manager.publish("test/topic", "Hello, MQTT!")