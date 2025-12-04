#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#define pin 16
const char* ssid = "Redmi A3";
const char* password = "Anoop@689102";

ESP8266WebServer server(80);

void setup() {
  pinMode(pin,OUTPUT);
  Serial.begin(115200);
  WiFi.begin(ssid, password);

  Serial.print("Connecting");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("Connected to WiFi");
  Serial.print("ESP IP Address: ");
  Serial.println(WiFi.localIP());

  // Handle command from Python
  server.on("/command", []() {
    String msg = server.arg("msg");
    Serial.print("Received command: ");
    Serial.println(msg);

    // -------- YOUR ACTIONS HERE ---------
    if (msg == "light_on") {
       digitalWrite(pin, HIGH);
       Serial.println("on");
    }
    if (msg == "light_off") {
       digitalWrite(pin, LOW);
       Serial.println("on");
    }

    server.send(200, "text/plain", "OK");
  });

  server.begin();
}

void loop() {
  server.handleClient();
}
