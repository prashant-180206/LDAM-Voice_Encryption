#include <SoftwareSerial.h>
SoftwareSerial BT(10, 11); // TX=10, RX=11

// Motor pins
const int ENA = 5; // Left motors
const int IN1 = 2;
const int IN2 = 3;

const int ENB = 6; // Right motors
const int IN3 = 4;
const int IN4 = 7;

String cmd;

// ---------------- MOTOR DIRECTIONS BASED ON YOUR TESTS ----------------

// LEFT MOTOR
void leftForward()
{ // robot backward direction
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, HIGH);
}
void leftBackward()
{ // robot forward direction
  digitalWrite(IN1, HIGH);
  digitalWrite(IN2, LOW);
}

// RIGHT MOTOR  (FIXED → this was wrong in your robot)
void rightForward()
{ // robot backward direction
  digitalWrite(IN3, HIGH);
  digitalWrite(IN4, LOW);
}
void rightBackward()
{ // robot forward direction
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, HIGH);
}

// ---------------- MOVEMENT FUNCTIONS ----------------

void forwardMove()
{
  Serial.println("Forward");
  leftBackward();  // forward
  rightBackward(); // forward
  analogWrite(ENA, 200);
  analogWrite(ENB, 200);
}

void backwardMove()
{
  Serial.println("Backward");
  leftForward();  // backward
  rightForward(); // backward
  analogWrite(ENA, 200);
  analogWrite(ENB, 200);
}

// ----------- LEFT: turn left then go forward -----------
void steerLeft()
{
  Serial.println("Left");

  // Phase 1: short left turn
  leftForward();   // push left wheel slightly backward
  rightBackward(); // right wheel forward

  analogWrite(ENA, 120); // slow left
  analogWrite(ENB, 200); // fast right
  delay(350);            // quick steering turn

  // Phase 2: go straight forward
  forwardMove();
}

// ----------- RIGHT: turn right then go forward -----------
void steerRight()
{
  Serial.println("Right");

  // Phase 1: short right turn
  leftBackward(); // left wheel forward
  rightForward(); // right wheel slightly backward

  analogWrite(ENA, 200);
  analogWrite(ENB, 120); // slow right
  delay(350);            // quick steering turn

  // Phase 2: go straight forward
  forwardMove();
}

void stopMotors()
{
  Serial.println("Stop");
  digitalWrite(IN1, LOW);
  digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);
  digitalWrite(IN4, LOW);
}

// ---------------- MAIN LOOP ----------------
void setup()
{
  Serial.begin(9600);
  BT.begin(9600);

  pinMode(ENA, OUTPUT);
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);

  pinMode(ENB, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  Serial.println("BT CONTROL READY");
}

void loop()
{
  if (BT.available())
  {
    cmd = BT.readStringUntil('\n');
    cmd.trim();
    cmd.toLowerCase();

    if (cmd == "forward")
      forwardMove();
    else if (cmd == "backward")
      backwardMove();
    else if (cmd == "right")
      steerLeft();
    else if (cmd == "left")
      steerRight();
    else if (cmd == "stop")
      stopMotors();
  }
}