const int sigPin = A0;

float analogOuts1[16];
const int s0 = 3;
const int s1 = 4;
const int s2 = 5;
const int s3 = 6;

int hasSensor1[2] = {0, 15};

const int enablePin = 2;



void setup() {
  Serial.begin(9600);
  pinMode(enablePin, OUTPUT);
  digitalWrite(enablePin, 0);  // low enable

  pinMode(s0, OUTPUT);
  pinMode(s1, OUTPUT);
  pinMode(s2, OUTPUT);
  pinMode(s3, OUTPUT);

  //Serial.println("-------------------------");
  for (int i = 0; i < 16; i++){
    analogOuts1[i] = -1.0;
  }
}

void printArr(float arr[], int n){
  for (int i = 0; i < n; i++){
    Serial.print(arr[i]);
    Serial.print("\t");
  }
  Serial.print("\n");
  //Serial.print("-------------------------");
}

void loop() {


  for (int i = 0; i < sizeof(hasSensor1); i++) {
    int sensor = hasSensor1[i];

    digitalWrite(s0, bitRead(sensor, 0));
    digitalWrite(s1, bitRead(sensor, 1));
    digitalWrite(s2, bitRead(sensor, 2));
    digitalWrite(s3, bitRead(sensor, 3));
    delayMicroseconds(10);
    analogOuts1[sensor] = analogRead(sigPin);
  }
  printArr(analogOuts1, 16);
  Serial.print("\n");

  delay(50);
}