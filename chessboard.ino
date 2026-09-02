int analogOuts[64];
int indexMap[64];

const int s0 = 3;
const int s1 = 4;
const int s2 = 5;
const int s3 = 6;

void setup() {
  delay(2000);
  Serial.begin(115200);

  pinMode(13, OUTPUT);
  digitalWrite(13, LOW);

  pinMode(12, OUTPUT);
  digitalWrite(12, LOW);

  pinMode(11, OUTPUT);
  digitalWrite(11, LOW);

  pinMode(10, OUTPUT);
  digitalWrite(10, LOW);

  pinMode(s0, OUTPUT);
  pinMode(s1, OUTPUT);
  pinMode(s2, OUTPUT);
  pinMode(s3, OUTPUT);

  for (int i = 0; i < 64; i++) {
    analogOuts[i] = -1;
  }

  for (int i = 0; i < 64; i++) {
    indexMap[i] = i;
  }

  for (int i = 0; i < 8; i++) {
    indexMap[i] = 7 - i;
  }
  for (int i = 0; i < 8; i++) {
    indexMap[8 + i] = 15 - i;
  }
}

void printArr(int arr[], int n) {
  for (int i = 0; i < n; i++) {
    Serial.print(arr[i]);
    if (i < n-1) Serial.print(" ");
  }
  Serial.print("\n");
}

void loop() {
  for (int i = 0; i < 16; i++) {
    digitalWrite(s0, bitRead(i, 0));
    digitalWrite(s1, bitRead(i, 1));
    digitalWrite(s2, bitRead(i, 2));
    digitalWrite(s3, bitRead(i, 3));

    analogOuts[indexMap[i]] = analogRead(A5); 
    analogOuts[indexMap[i + 16]] = analogRead(A4); 
    analogOuts[indexMap[i + 32]] = analogRead(A3); 
    analogOuts[indexMap[i + 48]] = analogRead(A2);
    delay(20);
  }
  
  printArr(analogOuts, 64);
}