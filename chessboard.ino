int sigPins[2] = {A0, A1};

float analogOuts[16];
const int s0 = 3;
const int s1 = 4;
const int s2 = 5;
const int s3 = 6;

void setup() {
  delay(2000);
  Serial.begin(9600);
  pinMode(13, OUTPUT);
  digitalWrite(13, LOW);

  pinMode(s0, OUTPUT);
  pinMode(s1, OUTPUT);
  pinMode(s2, OUTPUT);
  pinMode(s3, OUTPUT);

  for (int i = 0; i < 16; i++){
    analogOuts[i] = -1.0;
  }
}

void printArr(float arr[], int n){
  for (int i = 0; i < n; i++){
    Serial.print(arr[i]);
    Serial.print(" ");
  }
  Serial.print("\n");
}

void loop() {


  for (int i = 0; i < 16; i++) {
    digitalWrite(s0, bitRead(i, 0));
    digitalWrite(s1, bitRead(i, 1));
    digitalWrite(s2, bitRead(i, 2));
    digitalWrite(s3, bitRead(i, 3));
    delayMicroseconds(100);

    analogOuts[i] = analogRead(A0);
  }
  printArr(analogOuts, 16);
  Serial.print("\n");

  delay(0.05);
}