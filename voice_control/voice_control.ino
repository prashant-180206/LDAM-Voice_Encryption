

void setup() {
  Serial.begin(9600);
  while (!Serial); // Wait for serial monitor to open (useful for boards like Leonardo, Nano)

  Serial.println("✅ Arduino LED Controller Started");
  for (int pin = 2; pin <= 9; pin++) {
    pinMode(pin, OUTPUT);
    Serial.print("Intialized pin ");
    Serial.print(pin);
    Serial.println(" as OUTPUT");
  }
  Serial.println("Ready to receive commands...");
}

void loop() {
  // digitalWrite(3,HIGH);
  // delay(1000);
  // Serial.println("command");
  if (Serial.available() > 0) {
    int command = Serial.parseInt();

    // Clear any remaining newline or garbage
    Serial.read();

    if (command == 0 && Serial.peek() != '0') {
      // No valid number received
      Serial.println("⚠️ No valid command received");
      return;
    }

    Serial.print("📩 Received command: ");
    Serial.println(command);

    // Process command and blink corresponding LED
    if (command >= 2 && command <= 9) {
      Serial.print("💡 Blinking LED on pin ");
      Serial.println(command);
      digitalWrite(command, HIGH);
      delay(1000);
      digitalWrite(command, LOW);
      Serial.print("✅ Pin ");
      Serial.print(command);
      Serial.println(" turned OFF after 2s");
    } else {
      Serial.print("❌ Invalid pin command: ");
      Serial.println(command);
    }
  }
}
